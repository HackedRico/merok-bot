from __future__ import annotations

from tools.ship.clipboard import ClipboardPublisher
from tools.ship.dry_run import DryRunPublisher
from tools.ship.publisher import MAX_POST_CHARS, Publisher, validate_post
from tools.ship.x_api import XPublisher

# =============================================================================
# Module Overview
# =============================================================================
# Ship: where a post goes. One protocol, and adapters that differ only in the
# destination: X for real, the clipboard for platforms that lock apps out,
# and a dry run that exists for tests.

__all__ = ["Publisher", "XPublisher", "ClipboardPublisher", "DryRunPublisher", "validate_post", "MAX_POST_CHARS"]
