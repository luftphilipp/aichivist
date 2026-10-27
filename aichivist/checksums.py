"""Fixity: SHA-256 checksums (as in BagIt and most digital archives) and byte-for-byte comparison."""
import hashlib
from pathlib import Path
from typing import Dict

ALGORITHM = "sha256"
CHUNK = 1 << 20
QUICK_BYTES = 64 * 1024  # head + tail sample for cheap pre-filtering of duplicate candidates
IGNORED_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}  # OS housekeeping files, never records


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def quick_digest(path: Path) -> str:
    """Hash of size, first and last QUICK_BYTES. Equal quick digests are only candidates – confirm with digest()."""
    size = path.stat().st_size
    h = hashlib.sha256(str(size).encode())
    with open(path, "rb") as f:
        h.update(f.read(QUICK_BYTES))
        if size > QUICK_BYTES:
            f.seek(max(QUICK_BYTES, size - QUICK_BYTES))
            h.update(f.read(QUICK_BYTES))
    return h.hexdigest()


def is_record(path: Path) -> bool:
    return path.is_file() and path.name not in IGNORED_NAMES and not path.name.startswith(".aichivist")


def manifest(folder: Path) -> Dict[str, str]:
    """Relative POSIX path → SHA-256 for every record below folder."""
    return {p.relative_to(folder).as_posix(): digest(p) for p in sorted(folder.rglob("*"))
            if is_record(p) and not any(part.startswith(".aichivist") for part in p.relative_to(folder).parts)}


def same_content(a: Path, b: Path) -> bool:
    if a.is_file():
        return b.is_file() and a.stat().st_size == b.stat().st_size and digest(a) == digest(b)
    return b.is_dir() and manifest(a) == manifest(b)
