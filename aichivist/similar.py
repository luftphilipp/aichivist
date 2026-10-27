"""Near-duplicates: the same document in different files (a new scan, a re-download, another export).

Byte checksums only find identical files. Here the *text* is compared: word 3-grams ("shingles") and their overlap
(Jaccard similarity). Two scans of the same policy share almost all shingles even though their bytes differ.
"""
import re
from itertools import combinations
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Set

from . import fulltext
from .checksums import is_record

MIN_WORDS = 30          # shorter texts give unreliable similarity
DEFAULT_THRESHOLD = 0.8
WORD = re.compile(r"\w+", re.UNICODE)


class Similar(NamedTuple):
    first: str
    second: str
    similarity: float


def shingles(text: str, size: int = 3) -> Set[str]:
    words = [w.lower() for w in WORD.findall(text)]
    return {" ".join(words[i:i + size]) for i in range(len(words) - size + 1)} if len(words) >= MIN_WORDS else set()


def jaccard(a: Set[str], b: Set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def _documents(paths: Iterable[Path]) -> List[Path]:
    found: List[Path] = []
    for path in paths:
        files = [path] if path.is_file() else sorted(path.rglob("*"))
        found += [f for f in files if is_record(f) and not any(p.startswith(".") for p in f.parts[-3:-1])]
    return found


def find(paths: Iterable, area=None, threshold: float = DEFAULT_THRESHOLD) -> List[Similar]:
    """Pairs among `paths`, or between `paths` and `area`, whose text overlaps at least `threshold`."""
    new = _documents(Path(p) for p in paths)
    old = _documents([Path(area)]) if area else []
    texts: Dict[Path, Set[str]] = {f: shingles(fulltext.extract(f)[0]) for f in set(new) | set(old)}
    pairs = [(a, b) for a in new for b in old if a != b] if area else list(combinations(new, 2))
    hits = [Similar(str(a), str(b), round(jaccard(texts[a], texts[b]), 3)) for a, b in pairs]
    return sorted((h for h in hits if h.similarity >= threshold), key=lambda h: -h.similarity)
