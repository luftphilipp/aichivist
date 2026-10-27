"""Where aichivist keeps its state (journal, snapshots) and where trashed files go, per operating system."""
import os
import sys
from pathlib import Path
from typing import Optional


def full_path(path) -> Path:
    """User-supplied path → absolute path; "~" means the home folder even when the shell did not expand it."""
    return Path(path).expanduser().absolute()


def home_dir() -> Path:
    return Path(os.environ.get("AICHIVIST_HOME", str(Path.home() / ".aichivist"))).expanduser()


def journal_path() -> Path:
    return home_dir() / "journal.csv"


def snapshot_dir() -> Path:
    return home_dir() / "snapshots"


def trash_dir(src: Optional[Path] = None) -> Path:
    """macOS: the user's Trash. Linux: the freedesktop Trash. Windows: an own folder, because the
    Recycle Bin cannot be addressed by path and trashed files must stay restorable via `undo`.
    A file on another drive goes to that drive's own trash, as in the Finder: instant, no copy to the Mac."""
    override = os.environ.get("AICHIVIST_TRASH")
    if override:
        return Path(override).expanduser()
    volume = volume_trash(src) if src is not None else None
    if volume:
        return volume
    if sys.platform == "darwin":
        return Path.home() / ".Trash"
    if sys.platform.startswith("win"):
        return home_dir() / "trash"
    data_home = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(data_home) / "Trash" / "files"


def _existing(path: Path) -> Path:
    path = Path(os.path.realpath(path))
    while not path.exists():
        path = path.parent
    return path


def same_drive(a: Path, b: Path) -> bool:
    """Compared by device, not by path: on macOS /Users and /private lie on the same data volume."""
    return os.stat(_existing(a)).st_dev == os.stat(_existing(b)).st_dev


def mount_point(path: Path) -> Path:
    """The top folder of the drive that holds `path`."""
    path = _existing(path)
    device = os.stat(path).st_dev
    while path.parent != path and os.stat(path.parent).st_dev == device:
        path = path.parent
    return path


def volume_trash(src: Path) -> Optional[Path]:
    """<drive>/.Trashes/<uid> (macOS) or <drive>/.Trash-<uid>/files (Linux) for files on another drive than the home
    folder; None where that does not apply or the drive refuses it (then the home trash is used)."""
    if not hasattr(os, "getuid"):
        return None
    if same_drive(Path(src).parent, Path.home()):
        return None
    drive = mount_point(Path(src).parent)
    uid = str(os.getuid())
    folder = drive / ".Trashes" / uid if sys.platform == "darwin" else drive / f".Trash-{uid}" / "files"
    try:
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError:
        return None
    return folder
