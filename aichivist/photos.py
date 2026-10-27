"""Photos and videos by year: `<photos>/<year>/[<subject>/]<original name>` – as filing-plan proposals.

Year = capture date (EXIF for JPEG/TIFF/RAW, the movie header for MP4/MOV, Spotlight for HEIC on macOS), else a date
in the file name (IMG_20240512_…, 2024-05-12 …), else the file's modified date. Photos keep their names; a subject
folder they already lie in (e.g. "Holidays Ticino") is kept below the year. Nothing moves until the plan is approved.
"""
import os
import re
import struct
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterator, List, NamedTuple, Optional, Tuple

from . import plan
from .config import full_path

IMAGES = {".jpg", ".jpeg", ".heic", ".heif", ".png", ".gif", ".tif", ".tiff", ".webp", ".dng", ".cr2", ".cr3",
          ".nef", ".arw", ".raf", ".orf", ".rw2"}
VIDEOS = {".mov", ".mp4", ".m4v", ".3gp", ".avi", ".mts"}
TIFF_BASED = {".tif", ".tiff", ".dng", ".cr2", ".nef", ".arw", ".orf", ".rw2"}
SPOTLIGHT = {".heic", ".heif", ".cr3", ".raf", ".png", ".webp"}  # no built-in reader: ask Spotlight on macOS
HEADER_BYTES = 256 * 1024
NAME_DATE = re.compile(r"(?<!\d)((?:19|20)\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])(?!\d)")
EXIF_DATE = re.compile(r"^((?:19|20)\d{2}):(\d{2}):(\d{2})")
DATE_TAGS = (0x9003, 0x9004, 0x0132)  # DateTimeOriginal, DateTimeDigitized, DateTime
EXIF_POINTER = 0x8769
MAC_EPOCH = datetime(1904, 1, 1)
CONTAINERS = {b"moov", b"trak", b"mdia"}


class Photo(NamedTuple):
    path: Path
    taken: str     # YYYY-MM-DD
    source: str    # "camera", "file name" or "modified date"
    subject: str   # folder name kept below the year, or ""


def _valid(y: str, m: str, d: str) -> Optional[str]:
    try:
        found = date(int(y), int(m), int(d))
    except ValueError:
        return None
    return found.isoformat() if 1900 < found.year <= date.today().year + 1 else None


def _tiff_date(t: bytes) -> Optional[str]:
    """DateTimeOriginal (or DateTime) from a TIFF structure: the EXIF block of a JPEG, or a TIFF/RAW file itself."""
    if t[:2] not in (b"II", b"MM"):
        return None
    order = "<" if t[:2] == b"II" else ">"

    def entries(offset: int) -> Iterator[Tuple[int, int, int]]:
        if offset + 2 > len(t):
            return
        count = struct.unpack_from(order + "H", t, offset)[0]
        for i in range(count):
            at = offset + 2 + 12 * i
            if at + 12 > len(t):
                return
            tag, _, n, value = struct.unpack_from(order + "HHII", t, at)
            yield tag, n, value

    found = {}
    first = struct.unpack_from(order + "I", t, 4)[0]
    for tag, n, value in entries(first):
        if tag == EXIF_POINTER:
            found.update({sub: (sn, sv) for sub, sn, sv in entries(value)})
        found.setdefault(tag, (n, value))
    for tag in DATE_TAGS:
        if tag in found:
            n, offset = found[tag]
            match = EXIF_DATE.match(t[offset:offset + n].decode("ascii", "ignore"))
            if match and _valid(*match.groups()):
                return _valid(*match.groups())
    return None


def _jpeg_date(data: bytes) -> Optional[str]:
    at = 2
    while at + 4 <= len(data) and data[at] == 0xFF:
        length = int.from_bytes(data[at + 2:at + 4], "big")
        if data[at + 1] == 0xE1 and data[at + 4:at + 10] == b"Exif\0\0":
            return _tiff_date(data[at + 10:at + 2 + length])
        at += 2 + length
    return None


def _movie_date(path: Path) -> Optional[str]:
    """Creation time from the `mvhd` header of MP4/MOV (seconds since 1904); 0 means unknown."""
    with path.open("rb") as f:
        pos, stop = 0, path.stat().st_size
        while pos + 8 <= stop:
            f.seek(pos)
            size, kind = struct.unpack(">I4s", f.read(8))
            header = 8
            if size == 1:
                size, header = struct.unpack(">Q", f.read(8))[0], 16
            elif size == 0:
                size = stop - pos
            if kind in CONTAINERS:
                pos, stop = pos + header, pos + size
                continue
            if kind == b"mvhd":
                version = f.read(1)[0]
                f.read(3)
                seconds = struct.unpack(">Q", f.read(8))[0] if version == 1 else struct.unpack(">I", f.read(4))[0]
                if not seconds:
                    return None
                taken = MAC_EPOCH + timedelta(seconds=seconds)
                return _valid(str(taken.year), str(taken.month), str(taken.day))
            if size < header:
                return None
            pos += size
    return None


def _spotlight_date(path: Path) -> Optional[str]:
    if sys.platform != "darwin":
        return None
    try:
        out = subprocess.run(["mdls", "-raw", "-name", "kMDItemContentCreationDate", str(path)],
                             capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", out)
    return _valid(*match.groups()) if match else None


def camera_date(path: Path) -> Optional[str]:
    suffix = path.suffix.lower()
    try:
        if suffix in VIDEOS:
            return _movie_date(path)
        if suffix in SPOTLIGHT:
            return _spotlight_date(path)
        with path.open("rb") as f:
            head = f.read(HEADER_BYTES)
        return _tiff_date(head) if suffix in TIFF_BASED else _jpeg_date(head)
    except (OSError, struct.error, IndexError):
        return None  # damaged or unusual file: fall back to the name or the modified date


def date_taken(path: Path) -> Tuple[str, str]:
    found = camera_date(path)
    if found:
        return found, "camera"
    match = NAME_DATE.search(path.stem)
    named = _valid(*match.groups()) if match else None
    if named:
        return named, "file name"
    return datetime.fromtimestamp(path.stat().st_mtime).date().isoformat(), "modified date"


def is_media(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGES | VIDEOS and not path.name.startswith(".")


def find(inbox) -> List[Photo]:
    """Photos and videos in the inbox; the sub-folder they lie in becomes their subject."""
    root = full_path(inbox)
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        folder = Path(dirpath)
        subject = folder.relative_to(root).parts[0] if folder != root else ""
        for name in sorted(filenames):
            path = folder / name
            if is_media(path):
                taken, source = date_taken(path)
                found.append(Photo(path, taken, source, subject))
    return found


def target(photo: Photo, photos_root: Path) -> Path:
    year_folder = photos_root / photo.taken[:4]
    return (year_folder / photo.subject if photo.subject else year_folder) / photo.path.name


def propose(inbox, photos_root, plan_file) -> List[plan.Row]:
    """One plan row per photo or video: into its year (and subject) folder. Nothing moves yet."""
    root = full_path(photos_root)
    return [plan.add(plan_file, p.path, target(p, root), f"taken {p.taken} ({p.source})") for p in find(inbox)]
