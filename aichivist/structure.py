"""Structure advice: spot what makes a folder tree hard to use and propose simple fixes – no standards, just habits
that keep a personal archive easy: few top-level areas, shallow paths, folders by subject, no empty or one-file
folders. Simple fixes become filing-plan rows the person approves; regrouping is done with the agent.
"""
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, NamedTuple

from . import plan
from .checksums import is_record
from .config import full_path
from .i18n import t
from .inventory import is_unit

MAX_DEPTH = 4         # folders below the area; deeper paths are hard to find again
MAX_TOP_LEVEL = 10    # more top-level areas than this become hard to overview
ALMOST_EMPTY = 2      # a folder with this many files or fewer (and no sub-folders) can usually go
BY_TYPE = re.compile(r"^(pdfs?|scans?|images?|bilder|fotos?|photos?|docs?|dokumente|documents|files|dateien|"
                     r"downloads?|misc|sonstiges|diverses|varia|neuer ordner|new folder|untitled( folder)?|"
                     r"unbenannter ordner|temp|tmp|neu|new|archiv alt|old)( \d+)?$", re.IGNORECASE)
MESSAGES = {
    "too_many_top": "{n} top-level folders – group them into up to 10 areas (e.g. Personal, Finance, Work, Study)",
    "too_deep": "{folder}: {n} folders deep – flatten to at most 4 levels",
    "single_child": "{folder}: contains only one folder – that level can go",
    "almost_empty": "{folder}: only {n} file(s) – move them up and remove the folder",
    "empty": "{folder}: empty – can be removed",
    "by_type": "{folder}: sorted by file type, not subject – file its {n} files by what they are about",
    "same_name": "'{folder}' exists {n} times ({where}) – keep one place for this subject",
}


BUNDLES = {".app", ".bundle", ".framework", ".photoslibrary", ".lrdata", ".plugin", ".kext"}
SUBJECT_LEVELS = 2  # folder levels where the same name twice means a duplicated subject
EXAMPLES = 3  # per kind of problem in the printed report
TITLES = {"too_many_top": "too many top-level folders", "too_deep": "folders nested too deeply",
          "single_child": "folders that only contain one folder", "almost_empty": "folders with only 1–2 files",
          "empty": "empty folders", "by_type": "folders sorted by file type",
          "same_name": "folder names used several times"}


class Finding(NamedTuple):
    kind: str
    folder: str
    n: int
    detail: str = ""


class Report(NamedTuple):
    area: str
    folders: int
    findings: List[Finding]


def _folders(area: Path) -> Dict[Path, List[str]]:
    """Every folder below area (skipping hidden ones and project/data units) with its entry names."""
    found: Dict[Path, List[str]] = {}
    for dirpath, dirnames, filenames in os.walk(area):
        folder = Path(dirpath)
        if folder != area and (is_unit(folder, dirnames + filenames)
                                or folder.suffix.lower() in BUNDLES):  # before hidden .git is dropped
            dirnames.clear()  # a code project or data folder is one unit; its inside is not a filing structure
            continue
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        found[folder] = dirnames + [f for f in filenames if is_record(folder / f) and not f.startswith(".")]
    return found


def analyse(area) -> Report:
    root = full_path(area)
    folders = _folders(root)
    findings: List[Finding] = []
    top = [f for f in folders if f.parent == root]
    if len(top) > MAX_TOP_LEVEL:
        findings.append(Finding("too_many_top", ".", len(top)))
    by_name: Dict[str, List[str]] = defaultdict(list)
    for folder, entries in sorted(folders.items()):
        if folder == root:
            continue
        rel = folder.relative_to(root).as_posix()
        subdirs = [e for e in entries if (folder / e).is_dir()]
        files = [e for e in entries if not (folder / e).is_dir()]
        depth = len(folder.relative_to(root).parts)
        if depth <= SUBJECT_LEVELS:  # duplicate subjects matter where subjects live, not deep inside
            by_name[folder.name.lower()].append(rel)
        if depth > MAX_DEPTH and files:
            findings.append(Finding("too_deep", rel, depth))
        if not entries:
            findings.append(Finding("empty", rel, 0))
        elif len(subdirs) == 1 and not files:
            findings.append(Finding("single_child", rel, 1))
        elif not subdirs and len(files) <= ALMOST_EMPTY:
            findings.append(Finding("almost_empty", rel, len(files)))
        if BY_TYPE.match(folder.name) and files:
            findings.append(Finding("by_type", rel, len(files)))
    for name, places in sorted(by_name.items()):
        if len(places) > 1 and not BY_TYPE.match(name) and not name.isdigit():
            findings.append(Finding("same_name", Path(places[0]).name, len(places), ", ".join(places)))
    return Report(str(root), len(folders) - 1, findings)


def render(report: Report) -> List[str]:
    """One block per kind of problem: how many, and a few examples – readable even for large archives."""
    if not report.findings:
        return [t("{area}: {n} folders – the structure looks tidy.", area=report.area, n=report.folders)]
    lines = [t("{area}: {n} folders, {k} things to improve", area=report.area, n=report.folders,
               k=len(report.findings))]
    for kind in MESSAGES:
        items = [f for f in report.findings if f.kind == kind]
        if not items:
            continue
        if len(items) > EXAMPLES:
            lines.append(f"  {len(items)}x {t(TITLES[kind])}, " + t("e.g.:"))
        for f in items[:EXAMPLES]:
            lines.append("  - " + t(MESSAGES[kind], folder=f.folder, n=f.n, where=f.detail))
    lines.append(t("Nothing was changed. Simple fixes: `aichivist structure <folder> --plan plan.md`; "
                   "for regrouping, ask your AI to propose a leaner structure."))
    return lines


def propose(area, plan_file) -> List[plan.Row]:
    """Plan rows for the simple fixes: files of almost empty folders move one level up. Nothing moves yet."""
    root = full_path(area)
    rows = []
    for finding in analyse(root).findings:
        if finding.kind != "almost_empty":
            continue
        folder = root / finding.folder
        for f in sorted(p for p in folder.iterdir() if is_record(p) and not p.name.startswith(".")):
            target = folder.parent / f.name
            if not target.exists():
                rows.append(plan.add(plan_file, f, target, f"'{finding.folder}' holds only {finding.n} file(s)"))
    return rows
