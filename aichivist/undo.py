"""Undo logged file steps in reverse order, but only where the files are still where the journal says."""
from typing import List, Optional

from . import journal
from .apps import is_link_to, remove_link
from .fileops import present, relocate, remove_trashinfo
from .markers import closed_root

REVERSIBLE = {"move", "rename", "trash", "move_linked"}
FILE_STEPS = REVERSIBLE | {"folder_created"}


def open_steps() -> List[journal.Entry]:
    """File steps that have not been undone yet. An undo row (old=step.new, new=step.old) cancels the latest
    matching earlier step, so repeating `undo` never reverts the same step twice."""
    steps: List[journal.Entry] = []
    for entry in journal.read():
        if entry.action in FILE_STEPS:
            steps.append(entry)
        elif entry.action == "undo":
            for i in range(len(steps) - 1, -1, -1):
                if (steps[i].new, steps[i].old) == (entry.old, entry.new):
                    del steps[i]
                    break
    return steps


def undo(since: Optional[str] = None, inclusive: bool = True, last: Optional[int] = None) -> List[journal.Entry]:
    """Revert file steps (all, those from `since` on, or the `last` n). Returns the steps that were skipped.
    Notes such as close, protect or apply_plan are documentation, not file steps, and are never counted."""
    steps = open_steps()
    if since is not None:
        steps = [e for e in steps if e.time > since or (inclusive and e.time == since)]
    if last is not None:
        steps = steps[-last:] if last > 0 else []
    return [step for step in reversed(steps) if not _revert(step)]


def _revert(entry: journal.Entry) -> bool:
    old, new = journal.as_path(entry.old), journal.as_path(entry.new)
    if entry.action == "folder_created":
        if new and new.is_dir() and not any(new.iterdir()):
            new.rmdir()
            journal.write(new, "", "undo")
            return True
        return False
    if old is None or new is None or closed_root(new) or closed_root(old.parent):
        return False  # closed collections are only changed after an explicit reopen
    if entry.action == "move_linked" and is_link_to(old, new):
        remove_link(old)  # the link left behind goes; the original comes back to its place
    if present(new) and not present(old) and old.parent.exists():
        relocate(new, old)
        if entry.action == "trash":
            remove_trashinfo(new)
        journal.write(new, old, "undo")
        return True
    return False
