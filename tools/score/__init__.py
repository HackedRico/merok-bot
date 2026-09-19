from __future__ import annotations

from tools.score.baseline import author_baselines, baseline_for, leave_one_out_medians
from tools.score.model import Traction

# =============================================================================
# Module Overview
# =============================================================================
# Score: predict how a post will do against its author's own bar, and say
# why. `Traction` is the model; `baseline_for` measures the bar from an
# author's history; `leave_one_out_medians` builds that feature for training
# rows without leaking each row's own label.

__all__ = ["Traction", "author_baselines", "baseline_for", "leave_one_out_medians"]
