"""Catalog check: every record of an area is described in its catalog, and every catalog entry still exists.

Catalog format: Markdown tables whose first column is the path relative to the catalog's folder (backticks allowed);
under a heading that names a sub-folder ("## Insurance") the path may also be relative to that sub-folder.
An entry ending in "/" describes a whole folder (e.g. a set of photos) and covers everything inside it.
"""
import re
import unicodedata
from pathlib import Path
from typing import List, NamedTuple, Set

from .checksums import is_record
from .config import full_path
from .fileops import FilingError

SEPARATOR = re.compile(r"^:?-{3,}:?$")
# catalogs describe records; they are not records themselves
CATALOG_NAMES = {"_catalog.md", "_katalog.md", "_catalogue.md", "_catalogo.md"}
TO_DESCRIBE_HEADING = "## To describe"
GERMAN_HEADER = re.compile(r"^\|\s*`?(Datei|Pfad)`?\s*\|", re.MULTILINE | re.IGNORECASE)
HEADER_WORDS = {"file", "datei", "path", "pfad", "fichier", "chemin", "percorso", "archivo", "ruta"}


class CheckResult(NamedTuple):
    not_in_catalog: List[str]
    not_on_disk: List[str]

    @property
    def ok(self) -> bool:
        return not (self.not_in_catalog or self.not_on_disk)


def same_text(text: str) -> str:
    """One spelling for umlauts: macOS stores "ü" in file names as "u" + combining dots, typed text uses one "ü"."""
    return unicodedata.normalize("NFC", text)


def resolve(base: Path, section: str, cell: str) -> str:
    """Path of a catalog entry relative to the catalog's folder. Under a heading that names a sub-folder
    ("## Insurance"), entries may be written relative to that folder ("policy.pdf" → "Insurance/policy.pdf")."""
    if section and (base / section).is_dir() and not cell.startswith(section + "/") and not (base / cell).exists():
        return f"{section}/{cell}"
    return cell


def entries(catalog_file: Path) -> Set[str]:
    found = set()
    base, section = catalog_file.parent, ""
    for line in catalog_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
        if not line.lstrip().startswith("|"):
            continue
        cell = line.strip().strip("|").split("|")[0].strip().strip("`").strip()
        if cell and not SEPARATOR.match(cell) and cell.lower() not in HEADER_WORDS:
            found.add(same_text(resolve(base, section, cell)))
    return found


def records(area: Path, catalog_file: Path) -> List[str]:
    return sorted(
        same_text(p.relative_to(area).as_posix()) for p in area.rglob("*")
        if is_record(p) and p.name.lower() not in CATALOG_NAMES
        and not any(part.startswith(".") for part in p.relative_to(area).parts)
    )


TO_DESCRIBE = "⚠ to describe"
PREFILLED = "◇"  # automatic description, to be checked
# the added rows speak the catalog's language, judged from its table header – not the system language
WORDS = {
    "en": (TO_DESCRIBE_HEADING, "| File | Content | Search terms | Date |", TO_DESCRIBE),
    "de": ("## Zu beschreiben", "| Datei | Inhalt | Suchbegriffe | Datum |", "⚠ zu beschreiben"),
}
TO_DESCRIBE_MARKS = {words[2] for words in WORDS.values()}


def _words(text: str):
    return WORDS["de" if GERMAN_HEADER.search(text) else "en"]


def _row(area: Path, rel: str, prefill: bool, to_describe: str) -> str:
    if not prefill:
        return f"| {rel} | {to_describe} | | |\n"
    from .describe import suggest  # local import: describe reads documents (fulltext), catalog stays light
    s = suggest(area / rel)
    if not s["has_text"]:
        return f"| {rel} | {to_describe} | | |\n"
    content = f"{PREFILLED} " + (s["summary"] or s["suggested_name"])
    cells = [rel, content, ", ".join(s["keywords"]), s["date"] or ""]
    return "| " + " | ".join(str(c).replace("|", "/") for c in cells) + " |\n"


def add_missing(catalog_file, prefill: bool = False) -> List[str]:
    """Append a row for every uncatalogued file: "⚠ to describe", or with `prefill` a description read from the
    document and marked "◇" (automatic) – the agent then checks or replaces it with `describe`."""
    catalog_file = full_path(catalog_file)
    missing = check(catalog_file).not_in_catalog
    if missing:
        text = catalog_file.read_text(encoding="utf-8").rstrip("\n") + "\n"
        heading, header, to_describe = _words(text)
        rows = "".join(_row(catalog_file.parent, rel, prefill, to_describe) for rel in missing)
        headings = [line for line in text.splitlines() if line.startswith("## ")]
        if not headings or headings[-1] != heading:  # reuse a trailing "To describe" section
            text += f"\n{heading}\n{header}\n|---|---|---|---|\n"
        catalog_file.write_text(text + rows, encoding="utf-8")
    return missing


def describe(catalog_file, rel: str, content: str, search_terms: str, date: str) -> str:
    """Replace the "⚠ to describe" row of one file with its description (created by add_missing)."""
    catalog_file = full_path(catalog_file)
    cells = [c.replace("|", "/").strip() for c in (rel, content, search_terms, date)]
    lines = catalog_file.read_text(encoding="utf-8").split("\n")
    for i, line in enumerate(lines):
        parts = [c.strip() for c in line.strip().strip("|").split("|")]
        open_row = len(parts) > 1 and (parts[1] in TO_DESCRIBE_MARKS or parts[1].startswith(PREFILLED))
        if open_row and same_text(parts[0].strip("`")) == same_text(cells[0]):
            lines[i] = "| " + " | ".join(cells) + " |"
            catalog_file.write_text("\n".join(lines), encoding="utf-8")
            return lines[i]
    raise FilingError(f"no '{TO_DESCRIBE}' row for {rel} in {catalog_file}; run check-catalog --add-missing first")


def check(catalog_file) -> CheckResult:
    catalog_file = full_path(catalog_file)
    area = catalog_file.parent
    listed = entries(catalog_file)
    folders = tuple(e for e in listed if e.endswith("/"))
    on_disk = records(area, catalog_file)
    present = set(on_disk)
    return CheckResult(
        not_in_catalog=[r for r in on_disk if r not in listed and not r.startswith(folders)],
        not_on_disk=sorted(e for e in listed if e not in present and not (area / e).exists()
                           and not any(r.startswith(e) for r in on_disk if e.endswith("/"))),
    )
