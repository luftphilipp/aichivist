"""Gentle reminder: tell the person only when enough new files have piled up in an inbox (default 25).

Set up the daily run with `aichivist watch ~/Downloads --install` (see schedule.py).
Exit code 3 when the threshold is reached, so scripts can react; a system notification is shown where available.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, NamedTuple, Sequence

from .checksums import is_record
from .config import full_path
from .i18n import count as count_noun
from .i18n import t

DEFAULT_THRESHOLD = 25
REACHED = 3
WINDOWS_BALLOON = ("Add-Type -AssemblyName System.Windows.Forms; $n = New-Object System.Windows.Forms.NotifyIcon; "
                   "$n.Icon = [System.Drawing.SystemIcons]::Information; $n.Visible = $true; "
                   "$n.ShowBalloonTip(10000, 'aichivist', $env:AICHIVIST_MESSAGE, 'Info'); Start-Sleep 11; "
                   "$n.Dispose()")


class InboxCount(NamedTuple):
    inbox: str
    files: int


def count(inboxes: Sequence) -> List[InboxCount]:
    return [InboxCount(str(full_path(i)), sum(1 for f in full_path(i).iterdir()
                                             if is_record(f) and not f.name.startswith(".")))
            for i in inboxes]


def message(counts: List[InboxCount], threshold: int) -> str:
    full = [c for c in counts if c.files >= threshold]
    if not full:
        return ""
    where = ", ".join(f"{Path(c.inbox).name} ({c.files})" for c in full)
    waiting = count_noun(sum(c.files for c in full), "file")
    return t("{files} waiting in {where} – ask your AI to tidy up.", files=waiting, where=where)


def show(text: str) -> None:
    """System notification where it needs nothing extra; otherwise the printed line is all."""
    try:
        if sys.platform == "darwin" and shutil.which("osascript"):
            safe = text.replace('"', "'")
            subprocess.run(["osascript", "-e", f'display notification "{safe}" with title "aichivist"'], timeout=10,
                           check=False)
        elif sys.platform == "win32":
            # a balloon from the notification area; the text is passed via the environment, never as code
            subprocess.run(["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", WINDOWS_BALLOON],
                           env={**os.environ, "AICHIVIST_MESSAGE": text}, timeout=30, check=False)
        elif shutil.which("notify-send"):
            subprocess.run(["notify-send", "aichivist", text], timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        pass  # a missing notification must never break a scheduled run
