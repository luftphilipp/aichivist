"""Closed collections are marked by a small JSON file in their root folder."""
from pathlib import Path
from typing import Optional

from .config import full_path

MARKER = ".aichivist-closed.json"


def closed_root(path) -> Optional[Path]:
    """The closed area that contains path (or is path), if any."""
    current = full_path(path)
    for candidate in (current, *current.parents):
        if (candidate / MARKER).is_file():
            return candidate
    return None


def closed_inside(folder) -> Optional[Path]:
    """A closed collection somewhere below folder (moving the folder would carry it away), if any."""
    folder = full_path(folder)
    if not folder.is_dir():
        return None
    return next((m.parent for m in folder.rglob(MARKER) if m.is_file()), None)
