from __future__ import annotations

import shutil
import subprocess

import pytest

from tools.ship import ClipboardPublisher, DryRunPublisher, validate_post


def test_dry_run_records_and_returns_an_id() -> None:
    pub = DryRunPublisher()
    post = pub.post("  Thursday's town hall is at 6pm.  ")
    assert post.platform == "dry_run" and len(post.id) == 12 and pub.posted == ["Thursday's town hall is at 6pm."]


def test_validation_runs_before_any_side_effect() -> None:
    with pytest.raises(ValueError):
        validate_post("   ")
    with pytest.raises(ValueError):
        validate_post("x" * 281)
    with pytest.raises(ValueError):
        ClipboardPublisher("myspace")


@pytest.mark.skipif(shutil.which("pbcopy") is None or shutil.which("pbpaste") is None, reason="macOS clipboard only")
def test_clipboard_export_lands_on_the_clipboard() -> None:
    post = ClipboardPublisher("tiktok").post("copied for tiktok")
    assert post.platform == "tiktok"
    assert subprocess.run(["pbpaste"], capture_output=True, text=True).stdout == "copied for tiktok"
