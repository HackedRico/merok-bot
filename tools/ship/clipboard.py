from __future__ import annotations

import shutil
import subprocess

from shared.types import PostId
from tools.ship.publisher import validate_post

# =============================================================================
# Module Overview
# =============================================================================
# The export adapter for platforms that lock unaudited apps out of posting:
# the text lands on the clipboard and the person pastes it in the app.

PLATFORMS = ("tiktok", "instagram", "linkedin")


class ClipboardPublisher:
    """Adapter: copy the text to the system clipboard, tagged with the platform it is for."""

    name = "clipboard"

    def __init__(self, platform: str = "tiktok") -> None:
        if platform not in PLATFORMS:
            raise ValueError(f"platform must be one of {PLATFORMS}")
        self.platform = platform

    def post(self, text: str) -> PostId:
        cleaned = validate_post(text)
        tool = shutil.which("pbcopy") or shutil.which("xclip")
        if tool is None:
            raise FileNotFoundError("no clipboard tool found; install `xclip` or run on macOS")
        args = [tool] if tool.endswith("pbcopy") else [tool, "-selection", "clipboard"]
        subprocess.run(args, input=cleaned.encode(), check=True)
        return PostId(platform=self.platform, id="clipboard", url=None)
