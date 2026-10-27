"""Survey (Bestandsaufnahme): take stock of places before filing anything – read only, local only, no AI.

Reports per place: files, size, types, unclear document names, files unchanged for years, cloud-only placeholders
(counted, never opened – opening would download them), folders unsuitable for cloud sync, free space, drive health;
plus duplicates across all places.
"""
import os
import re
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple, Union

from . import drives
from .apps import kind_of
from .checksums import IGNORED_NAMES, digest, quick_digest
from .config import full_path
from .i18n import count
from .i18n import t as t_
from .inventory import PROJECT_MARKERS, is_unit

DOC_TYPES = {".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".xls", ".xlsx", ".ods", ".ppt", ".pptx", ".odp",
             ".pages", ".numbers", ".key"}
UNCLEAR = re.compile(r"^(unknown|untitled|unbenannt|document|dokument|scan|file|datei|download|attachment|anhang|"
                     r"new|neu|img|image|bild)?[\s_\-]*\d*$|\(\d+\)$|\b(copy|kopie)\b", re.IGNORECASE)
SYNC_HEAVY_NAMES = {"node_modules", ".git", ".venv", "venv", "__pycache__", ".tox"}
YEAR = 365 * 24 * 3600
MAC_DATALESS = 0x40000000  # SF_DATALESS: iCloud/OneDrive placeholder, content only in the cloud
WIN_CLOUD_ONLY = 0x400000 | 0x40000 | 0x1000  # RECALL_ON_DATA_ACCESS | RECALL_ON_OPEN | OFFLINE
EXAMPLES = 3
PROGRESS_EVERY = 50_000  # progress line on stderr for large places
SYNC_HEAVY_FILES = 1000  # from here a folder is named individually as unsuitable for cloud sync


class TypeStat(NamedTuple):
    extension: str
    files: int
    size: int


class Heavy(NamedTuple):
    folder: str
    files: int
    kind: str = "data"  # "project" (code, Git) or "data"


class Location(NamedTuple):
    path: str
    files: int
    size: int
    types: List[TypeStat]
    unclear: List[str]
    stale: List[str]
    stale_size: int
    cloud_only: int
    cloud_only_size: int
    heavy: List[Heavy]
    disk_total: int
    disk_free: int
    health: drives.DriveHealth
    programs: List[Tuple[str, str]]  # program data found here: (folder, kind) – to be left in place


class Report(NamedTuple):
    locations: List[Location]
    duplicate_groups: List[List[str]]
    duplicate_waste: int


def is_cloud_only(path: Path, st: os.stat_result) -> bool:
    if sys.platform == "darwin":
        return bool(getattr(st, "st_flags", 0) & MAC_DATALESS)
    if sys.platform.startswith("win"):
        return bool(getattr(st, "st_file_attributes", 0) & WIN_CLOUD_ONLY)
    return False


def _count_files(folder: Path) -> int:
    return sum(len(files) for _, _, files in os.walk(folder))


def _unit(place: Path, folder: Path, names: List[str]) -> Optional[Union[Heavy, Tuple[str, str]]]:
    """A folder that is one unit: program data (folder, kind) to leave alone, or a project/data folder (Heavy)."""
    if folder == place:
        return None
    rel = folder.relative_to(place).as_posix()
    kind = kind_of(folder, names)
    if kind and kind != "code project":
        return (rel, kind)
    if is_unit(folder, names):
        return Heavy(rel, _count_files(folder), "project" if PROJECT_MARKERS & set(names) else "data")
    return None


def _scan(place: Path, stale_years: int, local_files: List[Path], progress: bool = False,
          exclude: Sequence[Path] = ()) -> Location:
    files = size = stale_size = cloud = cloud_size = 0
    types: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
    unclear: List[str] = []
    stale: List[str] = []
    heavy: List[Heavy] = []
    programs: List[Tuple[str, str]] = []
    cutoff = time.time() - stale_years * YEAR
    for dirpath, dirnames, filenames in os.walk(place):
        folder = Path(dirpath)
        dirnames[:] = [d for d in dirnames if (folder / d).resolve() not in exclude]  # excluded: not even names
        unit = _unit(place, folder, dirnames + filenames)
        if unit:
            if isinstance(unit, Heavy):
                heavy.append(unit)
            else:
                programs.append(unit)
            dirnames.clear()  # a program, project or data folder is one unit: never inspected file by file
            continue
        for name in [d for d in dirnames if d in SYNC_HEAVY_NAMES]:
            heavy.append(Heavy((folder / name).relative_to(place).as_posix(), _count_files(folder / name), "project"))
        dirnames[:] = sorted(d for d in dirnames if d not in SYNC_HEAVY_NAMES and not d.startswith("."))
        for name in filenames:
            path = folder / name
            if name.startswith(".") or name in IGNORED_NAMES or path.is_symlink():
                continue
            st = path.stat()
            rel = path.relative_to(place).as_posix()
            files += 1
            size += st.st_size
            if progress and files % PROGRESS_EVERY == 0:
                print(f"  … {files:,} files in {place}", file=sys.stderr, flush=True)
            ext = path.suffix.lower() or "(none)"
            types[ext][0] += 1
            types[ext][1] += st.st_size
            if path.suffix.lower() in DOC_TYPES and UNCLEAR.search(path.stem):
                unclear.append(rel)
            if st.st_mtime < cutoff:
                stale.append(rel)
                stale_size += st.st_size
            if is_cloud_only(path, st):
                cloud += 1
                cloud_size += st.st_size
            elif st.st_size:
                local_files.append(path)
    usage = shutil.disk_usage(place)
    type_stats = sorted((TypeStat(e, c, s) for e, (c, s) in types.items()), key=lambda t: (-t.files, -t.size))
    return Location(str(place), files, size, type_stats, sorted(unclear), sorted(stale), stale_size, cloud, cloud_size,
                    sorted(heavy), usage.total, usage.free, drives.health(place), programs)


def _identical_groups(files: Sequence[Path]) -> List[List[Path]]:
    """Size → head/tail sample → full SHA-256; only files that collide at a cheap stage are hashed further."""
    groups: List[List[Path]] = []
    by_size: Dict[int, List[Path]] = defaultdict(list)
    for f in files:
        by_size[f.stat().st_size].append(f)
    for same_size in (g for g in by_size.values() if len(g) > 1):
        by_quick: Dict[str, List[Path]] = defaultdict(list)
        for f in same_size:
            by_quick[quick_digest(f)].append(f)
        for candidates in (g for g in by_quick.values() if len(g) > 1):
            by_full: Dict[str, List[Path]] = defaultdict(list)
            for f in candidates:
                by_full[digest(f)].append(f)
            groups += [sorted(g) for g in by_full.values() if len(g) > 1]
    return sorted(groups)


def run(places: Sequence, stale_years: int = 3, find_duplicates: bool = True, progress: bool = False,
        exclude: Sequence[Path] = ()) -> Report:
    local_files: List[Path] = []
    excluded = [full_path(e).resolve() for e in exclude]
    locations = [_scan(full_path(p), stale_years, local_files, progress, excluded) for p in places]
    groups = _identical_groups(local_files) if find_duplicates else []
    waste = sum(g[0].stat().st_size * (len(g) - 1) for g in groups)
    return Report(locations, [[str(p) for p in g] for g in groups], waste)


def as_dict(report: Report) -> dict:
    def plain(value):
        if hasattr(value, "_asdict"):
            return {k: plain(v) for k, v in value._asdict().items()}
        if isinstance(value, list):
            return [plain(v) for v in value]
        return value
    return plain(report)


def human(size: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _examples(items: List[str]) -> str:
    names = ", ".join(Path(i).name for i in items[:EXAMPLES])
    return t_(" (e.g. {names})", names=names) if items else ""


def render(report: Report) -> List[str]:
    lines = []
    for loc in report.locations:
        lines.append(t_("{place}: {files}, {size} - disk {free} free of {total}", place=loc.path,
                        files=count(loc.files, "file"), size=human(loc.size), free=human(loc.disk_free),
                        total=human(loc.disk_total)))
        top = " | ".join(f"{s.extension} {s.files:,} ({human(s.size)})" for s in loc.types[:5])
        lines.append(t_("  types: {top}", top=top) if top else t_("  empty"))
        if loc.unclear:
            lines.append(t_("  ! {n} with unclear names", n=count(len(loc.unclear), "document"))
                         + _examples(loc.unclear))
        if loc.stale:
            lines.append(t_("  ! {n} ({size}) unchanged for years", n=count(len(loc.stale), "file"),
                            size=human(loc.stale_size)) + _examples(loc.stale))
        if loc.cloud_only:
            lines.append(t_("  i {n} ({size}) only in the cloud - counted, not downloaded",
                            n=count(loc.cloud_only, "file"), size=human(loc.cloud_only_size)))
        for h in (h for h in loc.heavy if h.files >= SYNC_HEAVY_FILES):
            lines.append(t_("  ! keep out of cloud sync: {folder} ({n})", folder=h.folder, n=count(h.files, "file")))
        small_projects = [h for h in loc.heavy if h.files < SYNC_HEAVY_FILES and h.kind == "project"]
        if small_projects:
            lines.append(t_("  i {n} smaller code projects - keep them in Git rather than cloud sync",
                            n=len(small_projects)))
        for folder, kind in loc.programs[:EXAMPLES]:
            lines.append(t_("  ! program folder, keep it as it is: {folder} ({kind})", folder=folder, kind=t_(kind)))
        if len(loc.programs) > EXAMPLES:
            lines.append(t_("  … and {n} more program folders", n=len(loc.programs) - EXAMPLES))
        hp = loc.health
        extra = "".join([f", {hp.power_on_hours:,} h" if hp.power_on_hours else "",
                         f", {hp.temperature} C" if hp.temperature else ""])
        lines.append(t_("  drive health: {status}{extra} ({detail})", status=t_(hp.status), extra=extra,
                        detail=hp.detail))
    if report.duplicate_groups:
        files = sum(len(g) - 1 for g in report.duplicate_groups)
        first = report.duplicate_groups[0]
        lines.append(t_("{files} in {groups} waste {size} (e.g. {a} = {b})", files=count(files, "duplicate file"),
                        groups=count(len(report.duplicate_groups), "group"), size=human(report.duplicate_waste),
                        a=Path(first[1]).name, b=Path(first[0]).name))
    else:
        lines.append(t_("no duplicate files found"))
    lines.append(t_("Nothing was changed. Next: ask your agent to \"tidy up\" - it proposes a filing plan for you to "
                    "approve."))
    return lines
