"""Duplicates: byte-identical files between new items and a target area, and within the new items themselves."""
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple

from .checksums import digest, is_record, quick_digest
from .config import full_path


class Duplicate(NamedTuple):
    source: Path  # the new item that would go on the deletion list
    match: Path   # the identical file that stays


COPY_MARKER = re.compile(r"(\bcopy\b|\bkopie\b|\(\d+\)|[-_ ]\d$)", re.IGNORECASE)


def keep_first(path: Path) -> tuple:
    """Order in which identical files are kept: names without copy markers first, then shorter names."""
    return bool(COPY_MARKER.search(path.stem)), len(path.name), path.name


def records_in(path: Path) -> List[Path]:
    """Records in a file or folder, skipping hidden folders (system data, full-text index)."""
    if path.is_file():
        return [path] if is_record(path) else []
    return sorted((p for p in path.rglob("*")
                   if is_record(p) and not any(part.startswith(".") for part in p.relative_to(path).parts[:-1])),
                  key=keep_first)


class _Hashes:
    """Cached hashes: size → head/tail sample → full SHA-256, each only when the cheaper step collides."""

    def __init__(self):
        self.quick: Dict[Path, str] = {}
        self.full: Dict[Path, str] = {}

    def same(self, a: Path, b: Path) -> bool:
        for cache, fn in ((self.quick, quick_digest), (self.full, digest)):
            for p in (a, b):
                if p not in cache:
                    cache[p] = fn(p)
            if cache[a] != cache[b]:
                return False
        return True


def find(sources: Iterable, area) -> List[Duplicate]:
    """Identical files; the copy with the cleaner name is kept, the other goes on the deletion list."""
    area = full_path(area)
    by_size: Dict[int, List[Path]] = defaultdict(list)
    for p in records_in(area):
        by_size[p.stat().st_size].append(p)
    hashes = _Hashes()
    found = []
    for source in (full_path(s) for s in sources):
        for new in records_in(source):
            size = new.stat().st_size
            match = next((c for c in by_size[size] if c != new and hashes.same(c, new)), None)
            if match:
                found.append(Duplicate(new, match))
            else:
                by_size[size].append(new)  # later inbox files are compared against this one
    return found
