"""Check a rules file: unfilled template placeholders and filing-plan folders that do not exist."""
import re
from pathlib import Path
from typing import List, NamedTuple, Optional, Tuple

from .config import full_path

PLACEHOLDER = re.compile(r"<(?!!--)[^<>\n]{1,80}>")
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
CODE_PATH = re.compile(r"`([^`]*[/\\][^`]*)`")
CODE_SPAN = re.compile(r"`([^`]+)`")


class RulesCheck(NamedTuple):
    placeholders: List[Tuple[int, str]]  # (line number, placeholder)
    missing_folders: List[str]

    @property
    def ok(self) -> bool:
        return not (self.placeholders or self.missing_folders)


def _base(path_text: str) -> str:
    """The fixed part of a filing path: everything before the first <variable> part."""
    return re.split(r"[/\\]?<", path_text, maxsplit=1)[0].rstrip("/\\")


def _bases(text: str, rules_dir: Path) -> List[Path]:
    """Folders a relative path may refer to: the rules file's folder and every absolute folder the rules name
    (e.g. "iCloud = `~/Library/Mobile Documents/com~apple~CloudDocs/`")."""
    named = (Path(_base(span)).expanduser() for span in CODE_SPAN.findall(text) if _base(span))
    return [rules_dir] + [folder for folder in named if folder.is_absolute() and folder.is_dir()]


def _missing_folder(path_text: str, bases: List[Path]) -> Optional[str]:
    base = _base(path_text)
    if not base:  # path still starts with a placeholder such as <cloud> – reported as placeholder
        return None
    folder = Path(base).expanduser()
    if folder.is_absolute():
        return None if folder.exists() else base
    return None if any((b / folder).exists() for b in bases) else base


def _unfilled(span: str) -> List[str]:
    """Placeholders in a code span: only one the span starts with is still to be filled in (`<path to RULES.md>`);
    later ones are variables of a command or path (`aichivist inventory <inbox>`), and choices like
    `<Alex|Sam>` are variables too."""
    first = PLACEHOLDER.match(span.strip())
    return [first.group(0)] if first and "|" not in first.group(0) else []


def check(rules_file) -> RulesCheck:
    """In table rows, `<Subject>`, `<Year>` … after a filled-in base folder are variables of the filing plan, not
    placeholders; everything else in angle brackets (outside HTML comments) is still to be filled in."""
    rules_file = full_path(rules_file)
    text = COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), rules_file.read_text(encoding="utf-8"))
    bases = _bases(text, rules_file.parent)
    placeholders: List[Tuple[int, str]] = []
    missing: List[str] = []
    for number, line in enumerate(text.splitlines(), 1):
        paths = CODE_PATH.findall(line) if line.lstrip().startswith("|") else []
        for path_text in paths:
            folder = _missing_folder(path_text, bases)
            if folder and folder not in missing:
                missing.append(folder)
        placeholders += [(number, p) for span in CODE_SPAN.findall(line) for p in _unfilled(span)]
        prose = CODE_SPAN.sub(" ", line)
        placeholders += [(number, m.group(0)) for m in PLACEHOLDER.finditer(prose)]
    return RulesCheck(placeholders, missing)
