"""Filing plans: the agent proposes, the human approves, aichivist executes – and the plan becomes the record.

A plan is a Markdown table that people can read and edit in any editor:

    | ✓ | Source | Target | Reason |
    |---|---|---|---|
    | ? | /home/a/Downloads/scan.pdf | /home/a/Personal/Insurance/2026-01-01 Policy.pdf | health policy |

Marks: "?" proposed · "x" approved · "link" approved, leaving a link at the old place so programs keep working ·
"done" executed · "error: …" failed · anything else is skipped.
Target TRASH moves the source to the trash (deletion list).
A "|" inside a cell is written as "\\|"; a cell with spaces at its start or end is written in backticks.
"""
import re
from pathlib import Path
from typing import List, NamedTuple, Optional, Sequence, Tuple

from . import apps, fileops, journal
from .config import full_path
from .fileops import FilingError
from .i18n import t
from .markers import closed_root

TRASH = "TRASH"
SEPARATOR = re.compile(r"^:?-+:?$")
CELL_BORDER = re.compile(r"(?<!\\)\|")  # a "|" that is not written as "\|"
HEADER_LINE = re.compile(r"^\|\s*✓\s*\|", re.MULTILINE)
HEADER = "| ✓ | Source | Target | Reason |\n|---|---|---|---|\n"
PREAMBLE = ("# Filing plan\n\n"
            "Mark rows to execute with `x` in the first column, then run `aichivist plan apply <this file>`.\n"
            "`?` = proposed, `link` = approved, leave a link at the old place (for program data), `done` = executed,\n"
            "`error: …` = failed. Target `TRASH` = move to the trash.\n\n")


class Row(NamedTuple):
    mark: str
    source: str
    target: str
    reason: str


class Result(NamedTuple):
    done: int
    failed: int
    errors: Tuple[Tuple[str, str], ...] = ()  # (source, reason) per failed row


def _unquote(cell: str) -> str:
    cell = cell.strip().replace("\\|", "|")
    inner = cell[1:-1]
    return inner if len(cell) > 1 and cell[0] == cell[-1] == "`" and inner != inner.strip() else cell


def _quote(value: str) -> str:
    value = value.replace("|", "\\|")
    return f"`{value}`" if value != value.strip() else value


def _cells(line: str) -> List[str]:
    line = line.strip()
    line = line[1:] if line.startswith("|") else line
    line = line[:-1] if line.endswith("|") and not line.endswith("\\|") else line
    return [_unquote(c) for c in CELL_BORDER.split(line)]


def read(plan_file) -> List[Row]:
    """Rows of the plan table; tolerant of editors that pad cells or use alignment separators (| :--- |)."""
    rows: List[Row] = []
    in_table = False
    for line in Path(plan_file).read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            in_table = False if rows else in_table
            continue
        cells = _cells(line)
        if cells[0] == "✓":
            in_table = True
        elif in_table and not all(SEPARATOR.match(c) for c in cells):
            rows.append(Row(*(cells + [""] * 4)[:4]))
    return rows


def write(plan_file, rows: Sequence[Row]) -> None:
    path = Path(plan_file)
    text = path.read_text(encoding="utf-8") if path.exists() else PREAMBLE
    preamble = HEADER_LINE.split(text, maxsplit=1)[0]
    body = "".join("| " + " | ".join(_quote(c) for c in r) + " |\n" for r in rows)
    path.write_text(preamble + HEADER + body, encoding="utf-8")


def add(plan_file, source, target, reason: str) -> Row:
    row = Row("?", str(full_path(source)), target if target == TRASH else str(full_path(target)), reason)
    path = Path(plan_file)
    write(path, (read(path) if path.exists() else []) + [row])
    return row


def approve(plan_file, rows: Optional[Sequence[int]] = None, link: bool = False) -> int:
    """Mark proposed rows as approved (all, or the given 1-based row numbers). For the human, not the agent.
    `link`: approve them as `link` – a link stays at the old place so programs that use the files keep working."""
    current = read(plan_file)
    chosen = set(rows) if rows else set(range(1, len(current) + 1))
    mark = "link" if link else "x"
    updated = [r._replace(mark=mark) if i in chosen and r.mark == "?" else r for i, r in enumerate(current, 1)]
    write(plan_file, updated)
    return sum(1 for a, b in zip(current, updated) if a != b)


PENDING = ("?", "x", "link")


def _created_earlier(folder: Path, seen_targets: set) -> bool:
    """An earlier row of the plan moves a folder to `folder` (or to a folder above it)."""
    return any(Path(target) == folder or Path(target) in folder.parents for target in seen_targets)


def problem(row: Row, seen_targets: set, seen_sources: set, ctx: Optional[apps.Context] = None,
            create_folders: bool = False) -> Optional[str]:
    src = Path(row.source)
    if not src.exists():
        return t("source missing")
    if row.source in seen_sources:
        return t("same source as an earlier row")
    try:
        fileops.ensure_open(src, allow_closed=False, carried=True)
    except FilingError:
        return t("source is in (or contains) a closed collection")
    if ctx is not None:
        found = fileops.program_problems(src, None if row.target == TRASH else Path(row.target), row.mark == "link",
                                         ctx)
        if found:
            return t("a program may stop working – {reasons} (mark `link` to keep a link at the old place)",
                     reasons="; ".join(found))
    if row.target == TRASH:
        return None
    dst = Path(row.target)
    if dst.exists():
        return t("target exists (nothing would be overwritten)")
    if row.target in seen_targets:
        return t("same target as an earlier row")
    if not dst.parent.exists() and not create_folders and not _created_earlier(dst.parent, seen_targets):
        return t("target folder missing (new folders need approval: apply with --create-folders)")
    if closed_root(dst.parent):
        return t("target is in a closed collection")
    return None


def check(plan_file, create_folders: bool = False) -> List[Tuple[Row, Optional[str]]]:
    """Simulate the plan without touching any file."""
    targets: set = set()
    sources: set = set()
    results = []
    rows = read(plan_file)
    ctx = apps.context() if any(r.mark in PENDING for r in rows) else None
    for row in rows:
        if row.mark in PENDING:
            results.append((row, problem(row, targets, sources, ctx, create_folders)))
            targets.add(row.target)
            sources.add(row.source)
        else:
            results.append((row, None))
    return results


def apply(plan_file, create_folders: bool = False) -> Result:
    """Execute approved rows. `create_folders`: the person approved the new target folders the plan needs."""
    rows = read(plan_file)
    journal.write("", full_path(plan_file), "apply_plan")
    done = failed = 0
    errors: List[Tuple[str, str]] = []
    updated = []
    ctx = apps.context() if any(r.mark in ("x", "link") for r in rows) else None
    for row in rows:
        if row.mark not in ("x", "link"):
            updated.append(row)
            continue
        try:
            if row.target == TRASH:
                fileops.trash(row.source, ctx=ctx)
            else:
                fileops.move(row.source, row.target, create_folders, leave_link=row.mark == "link", ctx=ctx)
            updated.append(row._replace(mark="done"))
            done += 1
        except (FilingError, OSError) as err:
            updated.append(row._replace(mark=f"error: {err}"))
            errors.append((row.source, str(err)))
            failed += 1
    write(plan_file, updated)
    return Result(done, failed, tuple(errors))
