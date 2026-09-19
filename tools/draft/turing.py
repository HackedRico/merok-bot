from __future__ import annotations

from typing import Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from shared.embed import Embedder

# =============================================================================
# Module Overview
# =============================================================================
# The statistical Turing test from the sponsor's Digital Twin paper: a linear
# classifier over embeddings tries to tell drafts from real posts. Its
# cross-validated AUC is the score; 0.5 is indistinguishable.

MIN_REAL = 20


def turing_test(candidates: Sequence[str], real: Sequence[str], embedder: Embedder, seed: int = 7) -> float:
    """Cross-validated AUC of drafts versus real posts; near 0.5 means the drafts pass."""
    if len(candidates) < 2:
        raise ValueError("need at least two candidates")
    if len(real) < MIN_REAL:
        raise ValueError(f"need at least {MIN_REAL} real posts")
    rng = np.random.default_rng(seed)
    # Balance the classes so the AUC is about separability, not about how many of each there are.
    sample = min(len(real), max(len(candidates) * 4, MIN_REAL))
    chosen = [real[i] for i in rng.choice(len(real), sample, replace=False)]
    X = embedder.embed(list(candidates) + chosen)
    y = np.array([1] * len(candidates) + [0] * len(chosen))
    folds = min(5, len(candidates))
    clf = LogisticRegression(max_iter=500, class_weight="balanced")
    scores = cross_val_predict(clf, X, y, cv=StratifiedKFold(folds, shuffle=True, random_state=seed), method="predict_proba")[:, 1]
    return float(roc_auc_score(y, scores))
