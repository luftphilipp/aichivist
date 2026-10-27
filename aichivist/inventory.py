"""Inventory: what is new, changed, moved or removed in a folder since the last saved snapshot."""
import csv
import hashlib
import os
from pathlib import Path
from typing import Dict, Iterator, List, NamedTuple, Tuple

from . import config, journal
from .checksums import IGNORED_NAMES, digest
from .config import full_path

PROJECT_MARKERS = {".git", ".venv", "package.json", "pyproject.toml", "requirements.txt"}
DATA_DIR_NAMES = {"Daten", "data", "datasets"}
BULK_LIMIT = 150  # folders with more files directly inside are treated as one unit (data or image dumps)
UNIT = "UNIT"     # checksum placeholder for project/data folders


class Changes(NamedTuple):
    first_run: bool
    entries: List[str]
    new: List[str]
    changed: List[str]
    moved: List[Tuple[str, str]]
    removed: List[str]


def is_unit(folder: Path, names: List[str]) -> bool:
    if PROJECT_MARKERS & set(names) or folder.name in DATA_DIR_NAMES:
        return True
    return sum(1 for p in folder.iterdir() if p.is_file()) > BULK_LIMIT


def scan(root: Path) -> Iterator[Tuple[str, int, int]]:
    """(relative POSIX path, size, mtime) per file; project and data folders appear once as 'name/'."""
    for dirpath, dirnames, filenames in os.walk(root):
        folder = Path(dirpath)
        if folder != root and is_unit(folder, dirnames + filenames):
            dirnames.clear()
            yield folder.relative_to(root).as_posix() + "/", 0, 0
            continue
        dirnames[:] = sorted(n for n in dirnames if not n.startswith("."))
        for name in sorted(filenames):
            if name.startswith((".", "~$")) or name in IGNORED_NAMES:
                continue
            st = (folder / name).stat()
            yield (folder / name).relative_to(root).as_posix(), st.st_size, int(st.st_mtime)


def snapshot_file(root: Path) -> Path:
    key = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:12]  # file name only, not fixity
    return config.snapshot_dir() / f"{root.name or 'root'}_{key}.tsv"


def load(path: Path) -> Dict[str, Tuple[int, int, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {r[0]: (int(r[1]), int(r[2]), r[3]) for r in csv.reader(f, delimiter="\t")}


def write_snapshot(path: Path, entries: Dict[str, Tuple[int, int, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        for rel, (size, mtime, digest) in sorted(entries.items()):
            writer.writerow([rel, size, mtime, digest])


def diff(root, save: bool = False) -> Changes:
    root = full_path(root)
    snap = snapshot_file(root)
    old = load(snap)
    current = {}
    for rel, size, mtime in scan(root):
        prev = old.get(rel)
        if rel.endswith("/"):
            checksum = UNIT
        elif prev and prev[0] == size and prev[1] == mtime:
            checksum = prev[2]  # unchanged since last snapshot: reuse checksum
        else:
            checksum = digest(root / rel)
        current[rel] = (size, mtime, checksum)
    first_run = not snap.exists()  # an empty folder saved earlier is not a first run
    if save:
        write_snapshot(snap, current)
    return compare(old, current, first_run)


def manual_moves(root, changes: Changes) -> List[Tuple[str, str]]:
    """Moves not made through aichivist – usually a human correcting the agent; a hint to adapt the rules."""
    root = full_path(root)
    logged = {e.new for e in journal.read() if e.action in ("move", "rename")}
    return [(old, new) for old, new in changes.moved if str(root / new) not in logged]


def compare(old, current, first_run: bool) -> Changes:
    gone = {r: v for r, v in old.items() if r not in current}
    added = {r: v for r, v in current.items() if r not in old}
    by_digest = {v[2]: r for r, v in gone.items() if v[2] != UNIT}
    moved = sorted((by_digest[v[2]], r) for r, v in added.items() if v[2] in by_digest)
    moved_to = {new for _, new in moved}
    moved_from = {old_rel for old_rel, _ in moved}
    return Changes(
        first_run=first_run,
        entries=sorted(current),
        new=sorted(set(added) - moved_to),
        changed=sorted(r for r in current if r in old and current[r][2] != old[r][2]),
        moved=moved,
        removed=sorted(set(gone) - moved_from),
    )
