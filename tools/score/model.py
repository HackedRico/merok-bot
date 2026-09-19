from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timezone

import duckdb
import numpy as np
import pyarrow as pa
from sklearn.ensemble import HistGradientBoostingRegressor

from shared.data import curves, latest
from shared.embed import Embedder
from shared.types import AuthorBaseline, Context, Driver, Forecast
from tools.score import features as F
from tools.score.baseline import leave_one_out_medians

# =============================================================================
# Module Overview
# =============================================================================
# Gradient boosting over the feature matrix, target log1p(likes). One model
# for the final count; a second for likes at one hour when the training table
# carries snapshots inside the first hour. Drivers are counterfactual swaps
# against the training medians, so every number in a forecast has a reason.

HOUR_WINDOW_MIN = 60.0
MIN_ROWS_1H = 500
ANCHOR_HISTORY = 20
_TIME_FEATURES = ("hour_sin", "hour_cos")
_AUTHOR_FEATURES = ("author_median_log", "author_history_known")


@dataclass(frozen=True, slots=True)
class Evaluation:
    """Mean absolute error in log-likes for the model and for the median baseline, on held-out rows."""

    mae_model: float
    mae_median_baseline: float
    rows: int

    @property
    def beats_baseline(self) -> bool:
        return self.mae_model < self.mae_median_baseline


class Traction:
    """A fitted forecaster; build one with `Traction.fit`."""

    def __init__(self, model_1d: HistGradientBoostingRegressor, model_1h: HistGradientBoostingRegressor | None, medians: np.ndarray, mean_embedding: np.ndarray, embedder: Embedder) -> None:
        self._model_1d = model_1d
        self._model_1h = model_1h
        self._medians = medians
        self._mean_embedding = mean_embedding
        self._embedder = embedder

    # -----------------------------------------------------------------
    # Training
    # -----------------------------------------------------------------

    @classmethod
    def fit(cls, labelled: pa.Table, embedder: Embedder, max_rows: int | None = None, seed: int = 7) -> "Traction":
        """Train on a firehose table read through `shared.data`; labels are each tweet's final likes."""
        for col in ("id", "author_id", "body", "created_at", "like_count", "has_media", "version"):
            if col not in labelled.column_names:
                raise ValueError(f"labelled table is missing {col!r}; read it through `shared.data`")
        final = latest(labelled)
        if max_rows and final.num_rows > max_rows:
            rng = np.random.default_rng(seed)
            final = final.take(pa.array(np.sort(rng.choice(final.num_rows, max_rows, replace=False))))
        X, y = cls._matrix(final, embedder)
        if len(y) < 50:
            raise ValueError("need at least 50 rows to fit")
        model_1d = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, max_leaf_nodes=31, random_state=seed)
        model_1d.fit(X, y)

        model_1h = None
        hour_rows = cls._likes_at_one_hour(labelled)
        if hour_rows.num_rows >= MIN_ROWS_1H:
            Xh, yh = cls._matrix(hour_rows, embedder, likes_col="likes_1h")
            model_1h = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.06, random_state=seed)
            model_1h.fit(Xh, yh)

        named_block = X[:, : len(F.NAMES)]
        return cls(model_1d, model_1h, np.median(named_block, axis=0), X[:, len(F.NAMES):].mean(axis=0), embedder)

    @staticmethod
    def _matrix(final: pa.Table, embedder: Embedder, likes_col: str = "like_count") -> tuple[np.ndarray, np.ndarray]:
        authors = final.column("author_id").to_pylist()
        likes = [int(v or 0) for v in final.column(likes_col).to_pylist()]
        median, known = leave_one_out_medians(authors, likes)
        builder = F.FeatureBuilder(embedder)
        created = final.column("created_at").to_pylist()
        media = final.column("has_media").to_pylist()
        for i, text in enumerate(final.column("body").to_pylist()):
            posted = created[i] if created[i].tzinfo else created[i].replace(tzinfo=timezone.utc)
            # Training rows do not know which template they rode; velocity is a prediction-time signal,
            # so it is zero here and the model learns it only through what the text says.
            builder.add(text or "", float(median[i]), bool(known[i]), posted.astimezone(timezone.utc), bool(media[i]), 0.0)
        return builder.build(), np.log1p(np.asarray(likes, dtype=np.float32))

    @staticmethod
    def _likes_at_one_hour(labelled: pa.Table) -> pa.Table:
        """Rows whose last snapshot inside the first hour gives a one-hour label."""
        traj = curves(labelled)
        con = duckdb.connect()
        con.register("c", traj)
        con.register("t", latest(labelled))
        return con.execute(
            f"""
            WITH first_hour AS (
                SELECT id, arg_max(like_count, minutes) AS likes_1h
                FROM c WHERE minutes BETWEEN 5 AND {HOUR_WINDOW_MIN} GROUP BY id
            )
            SELECT t.*, f.likes_1h FROM t JOIN first_hour f USING (id)
            """
        ).to_arrow_table()

    # -----------------------------------------------------------------
    # Prediction
    # -----------------------------------------------------------------

    def predict(self, text: str, author: AuthorBaseline, context: Context) -> Forecast:
        """Forecast one post; `context` says what the text does not."""
        if not text.strip():
            raise ValueError("text is empty")
        feats = F.features_for(text, author, context, self._embedder)
        row = F.matrix_from(feats)
        log_1d = float(self._model_1d.predict(row)[0])
        raw_1d = max(math.expm1(log_1d), 0.0)
        raw_1h = max(math.expm1(float(self._model_1h.predict(row)[0])), 0.0) if self._model_1h is not None else None

        if author.posts >= ANCHOR_HISTORY:
            # The firehose rarely shows an author with thousands of likes, so the model's absolute level is
            # not trusted for a known account. The model supplies the multiplier: this post against a typical
            # post by the same author, with its content and timing swapped for the training medians.
            log_typical = float(self._model_1d.predict(self._typical(row))[0])
            relative = math.exp(log_1d - log_typical)
            likes_1d = author.median_likes * relative
            # When the hour model predicts at or above the day model, the hour figure carries no information; leave it out.
            likes_1h = likes_1d * (raw_1h / raw_1d) if raw_1h is not None and raw_1d > 0 and raw_1h < raw_1d else None
        else:
            relative = raw_1d / max(author.median_likes, 1.0)
            likes_1d, likes_1h = raw_1d, raw_1h

        return Forecast(
            likes_1d=likes_1d,
            likes_1h=likes_1h,
            relative_to_median=relative,
            drivers=self._drivers(row, log_1d),
        )

    def _typical(self, row: np.ndarray) -> np.ndarray:
        """The same author, a typical post: content and timing features at the training medians, embedding at the mean."""
        out = F.swap_embedding(row, self._mean_embedding)
        for i, name in enumerate(F.NAMES):
            if name not in _AUTHOR_FEATURES:
                out[0, i] = float(self._medians[i])
        return out

    def _drivers(self, row: np.ndarray, log_pred: float, top: int = 5) -> tuple[Driver, ...]:
        """Counterfactual effects: swap each named feature for the training median, and the embedding for its mean."""
        effects: list[Driver] = []
        for i, name in enumerate(F.NAMES):
            if name in _TIME_FEATURES:
                continue
            swapped = float(self._model_1d.predict(F.swap_named(row, i, float(self._medians[i])))[0])
            effect = log_pred - swapped
            if abs(effect) > 1e-6:
                effects.append(Driver(name=name, effect=effect, detail=F.describe(name, float(row[0, i]))))
        swapped = float(self._model_1d.predict(F.swap_embedding(row, self._mean_embedding))[0])
        effects.append(Driver(name="what_it_says", effect=log_pred - swapped, detail="the wording itself, against a typical post"))
        effects.sort(key=lambda d: -abs(d.effect))
        return tuple(effects[:top])

    # -----------------------------------------------------------------
    # Evaluation
    # -----------------------------------------------------------------

    def evaluate(self, holdout: pa.Table) -> Evaluation:
        """Compare the model with "predict the author's median" on rows it did not see."""
        final = latest(holdout)
        X, y = self._matrix(final, self._embedder)
        pred = self._model_1d.predict(X)
        # The median baseline predicts the leave-one-out author median where known, else the global median of zero.
        baseline = X[:, F.named_index("author_median_log")]
        return Evaluation(
            mae_model=float(np.mean(np.abs(pred - y))),
            mae_median_baseline=float(np.mean(np.abs(baseline - y))),
            rows=len(y),
        )
