"""Built-in OCR without extra installs: macOS Vision (via JavaScript for Automation) and Windows.Media.Ocr (via
Windows PowerShell). Returns text per page, or None when no built-in engine is available or recognition failed."""
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

HERE = Path(__file__).resolve().parent
TIMEOUT = 600  # seconds per document; long scans take a while
PAGE = re.compile(r"^=== Page \d+ ===$", re.MULTILINE)


def engine() -> Optional[str]:
    if sys.platform == "darwin" and shutil.which("osascript"):
        return "macos-vision"
    if sys.platform.startswith("win") and shutil.which("powershell.exe"):
        return "windows-ocr"
    return None


def _command(path: Path) -> Optional[List[str]]:
    kind = engine()
    if kind == "macos-vision":
        return ["osascript", "-l", "JavaScript", str(HERE / "ocr_mac.js"), str(path)]
    if kind == "windows-ocr":
        return ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HERE / "ocr_windows.ps1"),
                str(path)]
    return None


def recognize(path: Path) -> Optional[List[str]]:
    """Text per page (one entry for images), or None."""
    command = _command(path)
    if command is None:
        return None
    try:
        done = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    text = done.stdout.strip()
    pages = [p.strip() for p in PAGE.split(text)] if PAGE.search(text) else [text]
    pages = [p for p in pages if p or len(pages) == 1]
    return pages if any(p.strip() for p in pages) else None
