"""The single audit trail: every file operation is appended as one CSV row (time, old path, new path, action)."""
import csv
from datetime import datetime
from pathlib import Path
from typing import List, NamedTuple

from . import config

FIELDS = ["time", "old_path", "new_path", "action"]


class Entry(NamedTuple):
    time: str
    old: str
    new: str
    action: str


def write(old, new, action: str) -> None:
    path = config.journal_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(FIELDS)
        writer.writerow([datetime.now().isoformat(timespec="microseconds"), str(old), str(new), action])


def read() -> List[Entry]:
    path = config.journal_path()
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return [Entry(r["time"], r["old_path"], r["new_path"], r["action"]) for r in csv.DictReader(f)]


def as_path(value: str):
    return Path(value) if value else None
