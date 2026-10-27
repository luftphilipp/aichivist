"""Open vs. closed collections: close an area with a fixity manifest, verify it later, reopen on request."""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional

from . import fulltext, journal
from .checksums import ALGORITHM, manifest
from .config import full_path
from .fileops import FilingError
from .i18n import t
from .markers import MARKER, closed_inside, closed_root


class Status(NamedTuple):
    state: str  # "open" or "closed"
    root: Path
    closed_at: Optional[str] = None
    file_count: Optional[int] = None
    note: Optional[str] = None


def _load(root: Path) -> dict:
    return json.loads((root / MARKER).read_text(encoding="utf-8"))


def status(area) -> Status:
    area = full_path(area)
    root = closed_root(area)
    if root is None:
        return Status("open", area)
    data = _load(root)
    return Status("closed", root, data["closed_at"], len(data["files"]), data.get("note"))


def close(area, note: str = "") -> Status:
    area = full_path(area)
    if not area.is_dir():
        raise FilingError(t("not a folder: {area}", area=area))
    if closed_root(area):
        raise FilingError(t("already closed: {area}", area=closed_root(area)))
    if closed_inside(area):
        raise FilingError(t("{area} contains the closed collection {inner}; nested collections are not supported – "
                            "close the sub-folders separately", area=area, inner=closed_inside(area)))
    data = {"closed_at": datetime.now().isoformat(timespec="seconds"), "note": note,
            "algorithm": ALGORITHM, "files": manifest(area)}
    (area / MARKER).write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    fulltext.build(area)  # only closed collections get a full-text index
    journal.write(note, area, "close")
    return status(area)


def reopen(area, note: str = "") -> Status:
    area = full_path(area)
    root = closed_root(area)
    if root is None:
        raise FilingError(t("not closed: {area}", area=area))
    if root != area:
        raise FilingError(t("{area} is part of the closed collection {root}; reopen that folder", area=area, root=root))
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    (root / MARKER).rename(root / f".aichivist-reopened-{stamp}.json")  # keeps the old manifest as history
    fulltext.drop(root)  # an open collection changes; the index is rebuilt on the next close
    journal.write(note, root, "reopen")
    return status(root)


def recorded_manifest(area) -> Dict[str, str]:
    """The fixity manifest (relative path → SHA-256) written when the collection was closed."""
    root = closed_root(full_path(area))
    if root is None:
        raise FilingError(t("not closed: {area}", area=area))
    return _load(root)["files"]


def verify(area) -> Dict[str, List[str]]:
    """Compare a closed collection with the manifest written when it was closed."""
    root = closed_root(full_path(area))
    if root is None:
        raise FilingError(t("not closed, nothing to verify: {area}", area=area))
    recorded, current = _load(root)["files"], manifest(root)
    return {
        "changed": sorted(rel for rel in recorded if rel in current and current[rel] != recorded[rel]),
        "missing": sorted(rel for rel in recorded if rel not in current),
        "extra": sorted(rel for rel in current if rel not in recorded),
    }
