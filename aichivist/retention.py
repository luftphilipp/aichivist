"""Retention periods (Aufbewahrungsfristen): find records whose period is over and let the person choose per record –
move it into a long-term archive, or delete it (trash). Nothing happens without approval: rows go into a filing plan.
"""
import re
from datetime import date, datetime
from pathlib import Path
from typing import List, NamedTuple, Optional

from . import plan
from .checksums import is_record
from .config import full_path

NAME_DATE = re.compile(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?\b")


class Due(NamedTuple):
    path: str
    record_date: str
    age_years: float


def record_date(path: Path) -> date:
    """Date of the record: from the file name (YYYY[-MM[-DD]] prefix), otherwise the last modification."""
    match = NAME_DATE.match(path.name)
    if match and 1900 <= int(match.group(1)) <= 2100:
        return date(int(match.group(1)), int(match.group(2) or 12), int(match.group(3) or 28))
    return datetime.fromtimestamp(path.stat().st_mtime).date()


def due(area, years: float, today: Optional[date] = None) -> List[Due]:
    root, today = full_path(area), today or date.today()
    found = []
    for f in sorted(root.rglob("*")):
        if not is_record(f) or any(p.startswith(".") for p in f.relative_to(root).parts) or f.name.startswith("_"):
            continue
        age = (today - record_date(f)).days / 365.25
        if age >= years:
            found.append(Due(str(f), record_date(f).isoformat(), round(age, 1)))
    return found


def propose(area, years: float, plan_file, archive=None) -> List[plan.Row]:
    """One plan row per due record: target = same place inside the long-term archive (or TRASH without archive).
    The person decides per row: approve to archive, or change the target to TRASH to delete."""
    root = full_path(area)
    rows = []
    for item in due(root, years):
        source = Path(item.path)
        target = str(full_path(archive) / source.relative_to(root)) if archive else plan.TRASH
        choice = "keep in long-term archive, or set target to TRASH to delete" if archive else "delete"
        rows.append(plan.add(plan_file, source, target,
                             f"retention {years:g} years over (dated {item.record_date}) – {choice}"))
    return rows
