"""What lands in an inbox besides documents: running downloads, screenshots, installers, films and episodes.

Recognised by name and dates only – no file is opened here.
"""
import re
import time
from pathlib import Path
from typing import Optional

PARTIAL_SUFFIXES = (".download", ".crdownload", ".part", ".partial", ".opdownload")  # Safari, Chrome, Firefox …
STALL_SECONDS = 300   # a download that has not grown for this long has probably stopped
ACTIVE_SECONDS = 120  # changed this recently: still being written
SCREENSHOT = re.compile(
    r"^(?:Bildschirmfoto|Screenshot|Bildschirmaufnahme|Capture d[’']écran|Schermata|Captura de pantalla)"
    r"[ _-]+(\d{4})-(\d{2})-(\d{2})", re.IGNORECASE)
INSTALLERS = {".dmg", ".pkg", ".mpkg", ".app", ".exe", ".msi", ".appimage", ".deb", ".rpm"}
ARCHIVES = {".zip", ".rar", ".7z", ".tar", ".gz", ".tgz"}
VIDEOS = {".mkv", ".mp4", ".m4v", ".avi", ".mov", ".wmv", ".ts", ".webm", ".mts", ".3gp"}
EPISODE = re.compile(r"(?<![a-z0-9])s\d{1,2}e\d{1,3}(?![0-9])", re.IGNORECASE)
RELEASE = re.compile(r"(?<![a-z0-9])(?:2160p|1080p|720p|480p|4k|uhd|blu-?ray|remux|web-?dl|webrip|hdtv|bdrip|"
                     r"dvdrip|x264|x265|h\.?26[45]|hevc)(?![a-z0-9])", re.IGNORECASE)


def is_partial(path: Path) -> bool:
    """A download that is not finished yet (Safari bundle, Chrome/Firefox partial file)."""
    return path.name.lower().endswith(PARTIAL_SUFFIXES)


def last_change(path: Path) -> float:
    """Newest modification time – inside a Safari bundle the files, not the bundle itself."""
    if path.is_dir():
        times = [p.stat().st_mtime for p in path.rglob("*") if p.is_file()]
        if times:
            return max(times)
    return path.stat().st_mtime


def download_state(path: Path, now: Optional[float] = None) -> str:
    """"downloading", or "stalled" when nothing was written for STALL_SECONDS."""
    idle = (now or time.time()) - last_change(path)
    return "stalled" if idle > STALL_SECONDS else "downloading"


def still_written(path: Path, now: Optional[float] = None) -> bool:
    return is_partial(path) and (now or time.time()) - last_change(path) < ACTIVE_SECONDS


def screenshot_date(name: str) -> Optional[str]:
    """YYYY-MM-DD from a screenshot's default name (macOS, Windows, several languages), else None."""
    m = SCREENSHOT.match(name)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def media_kind(path: Path) -> Optional[str]:
    """"episode" or "film" for release-style names, "personal video" for other videos, else None."""
    if path.suffix.lower() not in VIDEOS:
        return None
    if EPISODE.search(path.stem):
        return "episode"
    if RELEASE.search(path.stem):
        return "film"
    return "personal video"


def package_kind(path: Path) -> Optional[str]:
    suffix = path.suffix.lower()
    return "installer" if suffix in INSTALLERS else "archive" if suffix in ARCHIVES else None
