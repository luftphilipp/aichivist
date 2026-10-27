"""Safe file operations: never overwrite, respect closed collections, verify cross-drive copies, log everything."""
import errno
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

from . import apps, config, journal
from .checksums import same_content
from .config import full_path  # noqa: F401 (re-exported for commands)
from .i18n import t
from .markers import closed_inside, closed_root

WINDOWS_NOT_SAME_DEVICE = 17
# drives such as exFAT cannot store file flags or permissions; content and dates are what matters
METADATA_REFUSED = {errno.EINVAL, errno.ENOTSUP, errno.EPERM}


class FilingError(Exception):
    """A filing rule would be broken; nothing was changed."""


def is_cross_device(err: OSError) -> bool:
    return err.errno == errno.EXDEV or getattr(err, "winerror", None) == WINDOWS_NOT_SAME_DEVICE


def ensure_open(path: Path, allow_closed: bool, carried: bool = False) -> None:
    """Refuse paths inside a closed collection; `carried` (moved/trashed items) also must not contain one."""
    if allow_closed:
        return
    root = closed_root(path)
    if root:
        raise FilingError(t("{path} is inside the closed collection {root}; reopen it first", path=path, root=root))
    inner = closed_inside(path) if carried else None
    if inner:
        raise FilingError(t("{path} contains the closed collection {inner}; reopen it first", path=path, inner=inner))


def present(path: Path) -> bool:
    """Exists – a link counts even when what it points to is gone."""
    return path.exists() or path.is_symlink()


def _keep_stat(src: Path, dst: Path) -> None:
    """Dates, permissions and flags; where the drive refuses flags or permissions, keep at least the dates."""
    try:
        shutil.copystat(src, dst)
    except OSError as err:
        if err.errno not in METADATA_REFUSED:
            raise
        st = os.stat(src)
        os.utime(dst, ns=(st.st_atime_ns, st.st_mtime_ns))


def _copy(src: Path, dst: Path) -> None:
    """Copy a file or folder with its dates; links inside that lead nowhere are copied as links."""
    if src.is_symlink() and not src.exists():
        os.symlink(os.readlink(src), dst)
    elif src.is_dir():
        dst.mkdir()
        for entry in src.iterdir():
            _copy(entry, dst / entry.name)
        _keep_stat(src, dst)
    else:
        shutil.copyfile(src, dst)
        _keep_stat(src, dst)


def relocate(src: Path, dst: Path) -> None:
    """Rename; between drives copy, verify byte for byte, and only then remove the original."""
    try:
        os.rename(src, dst)
        return
    except OSError as err:
        if not is_cross_device(err):
            raise
    if src.is_symlink():  # a link moves as a link, never as a copy of what it points to
        os.symlink(os.readlink(src), dst)
        src.unlink()
        return
    try:
        _copy(src, dst)
        if not same_content(src, dst):
            raise FilingError(t("copy of {src} did not match the original; original kept", src=src))
    except BaseException:
        _remove(dst)  # never leave a half copy behind; the original is untouched
        raise
    _remove(src)


def _remove(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def program_problems(src: Path, dst: Optional[Path], leave_link: bool, ctx: Optional[apps.Context]) -> List[str]:
    """A program depends on the source (harmless when a link stays behind), or the target is program data."""
    problems = [apps.target_risk(dst)] if dst else []
    if not leave_link:
        problems += apps.risks(src, ctx or apps.context())
    return [p for p in problems if p]


def check_programs(src: Path, dst: Optional[Path], leave_link: bool, ctx: Optional[apps.Context]) -> None:
    found = program_problems(src, dst, leave_link, ctx)
    if found and dst is None:
        raise FilingError(t("{src}: a program may stop working – {reasons}. If deleting it is intended, use "
                            "--app-data", src=src, reasons="; ".join(found)))
    if found:
        raise FilingError(t("{src}: a program may stop working – {reasons}. Adjust the program and use --app-data, "
                            "or keep a link at the old place with --leave-link", src=src, reasons="; ".join(found)))


def move(src, dst, create_folder: bool = False, allow_closed: bool = False, app_data: bool = False,
         leave_link: bool = False, ctx: Optional[apps.Context] = None) -> Path:
    src, dst = full_path(src), full_path(dst)
    if not present(src):
        raise FilingError(t("source missing: {src}", src=src))
    if present(dst):
        raise FilingError(t("target exists, nothing overwritten: {dst}", dst=dst))
    ensure_open(src, allow_closed, carried=True)
    ensure_open(dst.parent, allow_closed)
    if not app_data:
        check_programs(src, dst, leave_link, ctx)
    if not dst.parent.exists():
        if not create_folder:
            raise FilingError(t("target folder missing (new folders need approval): {folder}", folder=dst.parent))
        dst.parent.mkdir(parents=True)
        journal.write("", dst.parent, "folder_created")
    relocate(src, dst)
    if leave_link:
        try:
            apps.leave_link(src, dst)
        except OSError as err:
            relocate(dst, src)
            raise FilingError(t("could not leave a link at {src} ({err}); nothing moved. Files can only be linked "
                                "on the same drive", src=src, err=err)) from err
    journal.write(src, dst, "move_linked" if leave_link else "rename" if src.parent == dst.parent else "move")
    return dst


def trash(src, allow_closed: bool = False, app_data: bool = False, ctx: Optional[apps.Context] = None) -> Path:
    src = full_path(src)
    if not present(src):
        raise FilingError(t("source missing: {src}", src=src))
    ensure_open(src, allow_closed, carried=True)
    if not app_data:
        check_programs(src, None, False, ctx)
    bin_dir = config.trash_dir(src)
    bin_dir.mkdir(parents=True, exist_ok=True)
    target, n = bin_dir / src.name, 1
    while present(target):
        target = bin_dir / f"{src.stem} ({n}){src.suffix}"
        n += 1
    relocate(src, target)
    write_trashinfo(src, target)
    journal.write(src, target, "trash")
    return target


def _trashinfo(target: Path) -> Optional[Path]:
    """Freedesktop trash (Linux file managers): Trash/files/<name> is described by Trash/info/<name>.trashinfo;
    on other drives the trash is <drive>/.Trash-<uid>."""
    trash = target.parent.parent.name
    if target.parent.name == "files" and (trash == "Trash" or trash.startswith(".Trash-")):
        return target.parent.parent / "info" / f"{target.name}.trashinfo"
    return None


def write_trashinfo(original: Path, target: Path) -> None:
    info = _trashinfo(target)
    if info is None:
        return
    info.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    info.write_text(f"[Trash Info]\nPath={quote(str(original))}\nDeletionDate={stamp}\n", encoding="utf-8")


def remove_trashinfo(target: Path) -> None:
    info = _trashinfo(target)
    if info is not None and info.exists():
        info.unlink()
