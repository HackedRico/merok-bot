from __future__ import annotations

import random
from typing import Sequence

import duckdb
import pyarrow as pa

from shared.data import curves
from shared.types import CurvePoint, PostId

# =============================================================================
# Module Overview
# =============================================================================
# The replay adapter: a real tweet's snapshots from the firehose, served as
# if it were the post just shipped, in real minutes since it was created.
# Picks tweets with several observations and some likes so the curve has
# shape; the earliest observation is typically hours in, and that is shown
# as it is.

MIN_POINTS = 3


class ReplayPoller:
    """Adapter: replays a firehose trajectory chosen from a table read through `shared.data`."""

    name = "replay"

    def __init__(self, tweets: pa.Table, seed: int | None = None) -> None:
        traj = curves(tweets)
        con = duckdb.connect()
        con.register("c", traj)
        rows = con.execute(
            f"""
            SELECT id, list(struct_pack(minutes := minutes, likes := like_count) ORDER BY minutes) AS pts
            FROM c WHERE minutes >= 0
            GROUP BY id HAVING count(*) >= {MIN_POINTS} AND max(like_count) > 0
            """
        ).fetchall()
        if not rows:
            raise ValueError("no tweet in the table has enough snapshots to replay")
        self._trajectories = {r[0]: [CurvePoint(float(p["minutes"]), int(p["likes"])) for p in r[1]] for r in rows}
        self._rng = random.Random(seed)

    def trajectory(self, post: PostId, minutes: float) -> Sequence[CurvePoint]:
        chosen = self._trajectories[self._rng.choice(list(self._trajectories))]
        within = [p for p in chosen if p.minutes <= minutes]
        # If the window is shorter than the first observation, show the earliest point anyway; an empty curve says nothing.
        return within or chosen[:1]

    @property
    def available(self) -> int:
        """How many real trajectories the replay can draw from."""
        return len(self._trajectories)
