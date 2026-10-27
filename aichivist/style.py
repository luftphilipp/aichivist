"""Learn the person's naming style: past renames from the journal and existing names per folder of an area.

The agent shows these examples to itself before proposing names, so new names match the old ones.
"""
from pathlib import Path
from typing import Any, Dict, List

from . import journal
from .checksums import is_record
from .config import full_path

PER_FOLDER = 5
RECENT = 20


def examples(area, recent: int = RECENT, per_folder: int = PER_FOLDER) -> Dict[str, Any]:
    root = full_path(area)
    renames = [{"before": Path(e.old).name, "after": Path(e.new).name, "folder": str(Path(e.new).parent)}
               for e in journal.read()
               if e.action in ("move", "rename") and e.new and (Path(e.new) == root or root in Path(e.new).parents)]
    folders: Dict[str, List[str]] = {}
    for f in sorted(root.rglob("*")):
        rel_parts = f.relative_to(root).parts
        if not is_record(f) or any(p.startswith(".") for p in rel_parts) or f.name.lower().startswith("_"):
            continue
        names = folders.setdefault(f.parent.relative_to(root).as_posix() or ".", [])
        if len(names) < per_folder:
            names.append(f.name)
    return {"recent_renames": renames[-recent:], "names_per_folder": folders}
