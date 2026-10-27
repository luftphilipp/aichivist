"""Tools for agents without file access of their own (e.g. Claude Desktop via MCP).

Every path must lie inside the folders the person shared when starting the server (--root). Paths are resolved
first, so `..` and symlinks cannot escape. Moving files is only possible through filing plans.
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import (
    apps,
    catalog,
    config,
    describe,
    duplicates,
    fulltext,
    inventory,
    lifecycle,
    photos,
    plan,
    retention,
    review,
    similar,
    storage,
    structure,
    style,
    survey,
)
from .config import full_path
from .fileops import FilingError

PLAN_NAME = re.compile(r"^[\w .-]{1,60}$")
DEFAULT_MAX_CHARS = 20_000
LIST_LIMIT = 300


class Workspace:
    def __init__(self, roots: List, rules=None, exclude: Optional[List] = None):
        self.roots = [full_path(r).resolve() for r in roots]
        self.rules = full_path(rules) if rules else None
        self.exclude = [full_path(e).resolve() for e in exclude or []]

    def excluded(self, path: Path) -> bool:
        return any(path == e or e in path.parents for e in self.exclude)

    def check(self, path) -> Path:
        resolved = full_path(path).resolve()
        if not any(resolved == r or r in resolved.parents for r in self.roots):
            raise FilingError(f"{path} is outside the folders shared with aichivist")
        if self.excluded(resolved):
            raise FilingError(f"{path} is in an excluded folder; aichivist does not open it")
        return resolved

    def _plan_file(self, name: str) -> Path:
        if not PLAN_NAME.match(name):
            raise FilingError("plan names may contain letters, digits, spaces, dots, dashes and underscores")
        folder = config.home_dir() / "plans"
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{name}.md"

    # ---- reading -------------------------------------------------------------
    def get_rules(self) -> Dict[str, Any]:
        if not self.rules or not self.rules.exists():
            return {"rules": None, "note": "No rules file configured – ask the person where things belong before "
                                           "proposing a plan, and suggest writing rules (templates/RULES.md)."}
        return {"rules": self.rules.read_text(encoding="utf-8"), "path": str(self.rules)}

    def survey(self, paths: List[str], stale_years: int = 3) -> Dict[str, Any]:
        report = survey.run([self.check(p) for p in paths], stale_years=stale_years, exclude=self.exclude)
        return survey.as_dict(report)

    def list_folder(self, path: str) -> Dict[str, Any]:
        folder = self.check(path)
        entries = [{"name": p.name, "kind": "folder" if p.is_dir() else "file",
                    "size": p.stat().st_size if p.is_file() else None}
                   for p in sorted(folder.iterdir()) if not p.name.startswith(".") and not self.excluded(p.resolve())]
        return {"path": str(folder), "entries": entries[:LIST_LIMIT], "truncated": len(entries) > LIST_LIMIT}

    def read_document(self, path: str, max_chars: int = DEFAULT_MAX_CHARS) -> Dict[str, Any]:
        file = self.check(path)
        if not file.is_file():
            raise FilingError(f"not a file: {path}")
        text, method = fulltext.extract(file)
        return {"path": str(file), "method": method, "text": text[:max_chars], "characters": len(text),
                "truncated": len(text) > max_chars}

    def inventory(self, path: str) -> Dict[str, Any]:
        folder = self.check(path)
        changes = inventory.diff(folder)
        by_hand = inventory.manual_moves(folder, changes)

        def visible(rel: str) -> bool:
            return not self.excluded((folder / rel.rstrip("/")).resolve())
        return {"entries": [e for e in changes.entries if visible(e)], "first_run": changes.first_run,
                "new": [e for e in changes.new if visible(e)],
                "moved": [{"from": o, "to": n, "by_hand": (o, n) in by_hand} for o, n in changes.moved
                          if visible(o) and visible(n)]}

    def find_duplicates(self, paths: List[str], area: str) -> List[Dict[str, str]]:
        found = duplicates.find([self.check(p) for p in paths], self.check(area))
        return [{"source": str(d.source), "match": str(d.match)} for d in found
                if not self.excluded(d.source.resolve()) and not self.excluded(d.match.resolve())]

    def find_similar(self, paths: List[str], area: Optional[str] = None, threshold: float = 0.8) -> List[Dict]:
        hits = similar.find([self.check(p) for p in paths], self.check(area) if area else None, threshold)
        return [h._asdict() for h in hits]

    def suggest_name(self, path: str) -> Dict[str, Any]:
        return describe.suggest(self.check(path))

    def naming_examples(self, area: str) -> Dict[str, Any]:
        return style.examples(self.check(area))

    def structure_advice(self, area: str) -> Dict[str, Any]:
        report = structure.analyse(self.check(area))
        return {"findings": [f._asdict() for f in report.findings], "summary": structure.render(report)}

    def retention_due(self, area: str, years: float) -> List[Dict[str, Any]]:
        return [d._asdict() for d in retention.due(self.check(area), years)]

    # ---- filing plans --------------------------------------------------------
    def plan_add(self, source: str, target: str, reason: str, plan_name: str = "current") -> Dict[str, str]:
        checked_target = target if target == plan.TRASH else str(self.check(target))
        return plan.add(self._plan_file(plan_name), self.check(source), checked_target, reason)._asdict()

    def plan_show(self, plan_name: str = "current") -> Dict[str, Any]:
        file = self._plan_file(plan_name)
        rows = [r._asdict() for r in plan.read(file)] if file.exists() else []
        return {"plan": str(file), "rows": rows}

    def plan_check(self, plan_name: str = "current", create_folders: bool = False) -> Dict[str, Any]:
        results = plan.check(self._plan_file(plan_name), create_folders)
        return {"problems": [{"row": i, "source": r.source, "problem": p}
                             for i, (r, p) in enumerate(results, 1) if p]}

    def plan_approve(self, plan_name: str = "current", rows: Optional[List[int]] = None,
                     leave_link: bool = False) -> Dict[str, int]:
        return {"approved": plan.approve(self._plan_file(plan_name), rows, leave_link)}

    def storage_check(self, table_file: str) -> Dict[str, Any]:
        table = self.check(table_file)
        if not table.exists():
            return {"error": "table missing", "example": storage.EXAMPLE}
        return storage.as_dict(storage.check(table))

    def program_check(self, paths: List[str]) -> Dict[str, List[str]]:
        ctx = apps.context()
        return {p: apps.risks(self.check(p), ctx) for p in paths}

    def plan_review(self, plan_name: str = "current") -> Dict[str, str]:
        url = review.serve(self._plan_file(plan_name), open_browser=True, block=False)
        return {"url": url, "note": "The person reviews the plan in the browser and approves rows there."}

    def plan_apply(self, plan_name: str = "current", create_folders: bool = False) -> Dict[str, object]:
        file = self._plan_file(plan_name)
        for row in plan.read(file):  # a plan file could have been edited – re-check every approved row
            if row.mark in ("x", "link"):
                self.check(row.source)
                if row.target != plan.TRASH:
                    self.check(row.target)
        return plan.apply(file, create_folders)._asdict()

    def plan_photos(self, inbox: str, photos_root: str, plan_name: str = "current") -> Dict[str, Any]:
        rows = photos.propose(self.check(inbox), self.check(photos_root), self._plan_file(plan_name))
        return {"proposed": len(rows), "rows": [r._asdict() for r in rows]}

    # ---- catalogs and collections ---------------------------------------------
    def catalog_check(self, catalog_file: str, add_missing: bool = False, prefill: bool = True) -> Dict[str, Any]:
        file = self.check(catalog_file)
        added = catalog.add_missing(file, prefill=prefill) if add_missing else []
        return {"added": added, **catalog.check(file)._asdict()}

    def catalog_describe(self, catalog_file: str, file: str, content: str, search_terms: str,
                         date: str) -> Dict[str, str]:
        return {"row": catalog.describe(self.check(catalog_file), file, content, search_terms, date)}

    def status(self, path: str) -> Dict[str, Any]:
        return {k: str(v) if v is not None else None for k, v in lifecycle.status(self.check(path))._asdict().items()}

    def verify(self, path: str) -> Dict[str, List[str]]:
        return lifecycle.verify(self.check(path))

    def search(self, path: str, query: str) -> List[Dict[str, Any]]:
        return [h._asdict() for h in fulltext.search(self.check(path), query)]
