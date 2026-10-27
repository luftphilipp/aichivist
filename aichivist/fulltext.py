"""Full-text index for CLOSED collections only: built when an area is closed, dropped when it is reopened.

Open collections still change, so an index would go stale; closed ones are final, so text is extracted once and
searched without re-reading the originals. Extraction is local only (no network).
"""
import html
import importlib.util
import logging
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

from . import ocr
from .catalog import CATALOG_NAMES
from .checksums import is_record
from .config import full_path
from .fileops import FilingError
from .markers import closed_root

INDEX = ".aichivist-fulltext"
REPORT = "_report.tsv"
TEXT_TYPES = {".txt", ".md", ".csv", ".tsv", ".json", ".html", ".htm", ".xml", ".py", ".r", ".tex", ".ipynb"}
IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
SLIDE = re.compile(r"ppt/slides/slide(\d+)\.xml")
SECTION = re.compile(r"^=== (?:Page|Slide) (\d+) ===$", re.MULTILINE)
SNIPPET = 60
OCR_TIMEOUT = 1800  # seconds per document; large scans take a while


class Hit(NamedTuple):
    file: str
    page: int  # 0 = document without pages
    snippet: str


def index_dir(root) -> Path:
    return Path(root) / INDEX


def _xml_text(xml: str, paragraph_tag: str) -> str:
    parts = re.split(f"</{paragraph_tag}>", xml)
    return "\n".join(html.unescape(re.sub(r"<[^>]+>", "", p)).strip() for p in parts if p.strip()).strip()


def _slide_number(name: str) -> int:
    """1, 2, … for ppt/slides/slideN.xml (numeric order: 2 before 10), 0 for other entries."""
    match = SLIDE.fullmatch(name)
    return int(match.group(1)) if match else 0


def _office(path: Path) -> Tuple[str, str]:
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if path.suffix.lower() == ".docx":
            return _xml_text(z.read("word/document.xml").decode("utf-8"), "w:p"), "docx"
        if path.suffix.lower() == ".pptx":
            slides = sorted((n for n in names if _slide_number(n)), key=_slide_number)
            text = "\n".join(f"=== Slide {i} ===\n{_xml_text(z.read(n).decode('utf-8'), 'a:p')}"
                             for i, n in enumerate(slides, 1))
            return text, "pptx"
        shared = "xl/sharedStrings.xml"
        return (_xml_text(z.read(shared).decode("utf-8"), "si") if shared in names else ""), "xlsx"


def _pages(pages: List[str]) -> str:
    return "\n".join(f"=== Page {i} ===\n{t.strip()}" for i, t in enumerate(pages, 1))


def _pdf_text_layer(path: Path) -> Optional[List[str]]:
    """Text per page from the PDF's own text layer, or None if pypdf is not installed."""
    if importlib.util.find_spec("pypdf") is None:
        return None
    logging.getLogger("pypdf").setLevel(logging.ERROR)  # damaged files are reported by us, not logged by pypdf
    from pypdf import PdfReader
    return [p.extract_text() or "" for p in PdfReader(path).pages]


def _ocrmypdf(path: Path) -> List[str]:
    """OCR a scan with OCRmyPDF into a temporary copy; only the text sidecar is kept, the original is untouched."""
    with tempfile.TemporaryDirectory() as tmp:
        sidecar, out = Path(tmp) / "text.txt", Path(tmp) / "out.pdf"
        subprocess.run(["ocrmypdf", "--sidecar", str(sidecar), "--skip-text", "--quiet", str(path), str(out)],
                       capture_output=True, text=True, timeout=OCR_TIMEOUT, check=False)
        return sidecar.read_text(encoding="utf-8").split("\f") if sidecar.exists() else []


def _pdf(path: Path) -> Tuple[str, str]:
    pages = _pdf_text_layer(path)
    if pages and any(t.strip() for t in pages):
        return _pages(pages), "pdf"
    builtin = ocr.recognize(path)  # macOS Vision / Windows OCR – no installs needed
    if builtin:
        return _pages(builtin), "pdf+ocr (built-in)"
    if shutil.which("ocrmypdf"):
        ocr_pages = _ocrmypdf(path)
        if any(t.strip() for t in ocr_pages):
            return _pages(ocr_pages), "pdf+ocr"
    if pages is None:
        return "", "unavailable: PDF text needs `pip install aichivist[pdf]` (or ocrmypdf)"
    return _pages(pages), "pdf (no text layer: scan – no built-in OCR here, install ocrmypdf)"


def _ocr(path: Path) -> Tuple[str, str]:
    builtin = ocr.recognize(path)
    if builtin:
        return builtin[0], "ocr (built-in)"
    if not shutil.which("tesseract"):
        return "", "unavailable: no built-in OCR on this system – install tesseract"
    out = subprocess.run(["tesseract", str(path), "stdout"], capture_output=True, text=True, timeout=300)
    return out.stdout.strip(), "ocr"


def extract(path: Path) -> Tuple[str, str]:
    """(text, method). Never guesses: unsupported or unavailable types return empty text and say why."""
    suffix = path.suffix.lower()
    try:
        if suffix in TEXT_TYPES:
            return path.read_text(encoding="utf-8", errors="replace"), "text"
        if suffix in {".docx", ".pptx", ".xlsx"}:
            return _office(path)
        if suffix == ".pdf":
            return _pdf(path)
        if suffix in IMAGE_TYPES:
            return _ocr(path)
    except (OSError, KeyError, ValueError, zipfile.BadZipFile, subprocess.SubprocessError) as err:
        return "", f"error: {err}"
    except Exception as err:  # third-party parsers (pypdf) raise their own types; one bad file must not stop a close
        return "", f"error: unreadable ({type(err).__name__})"
    return "", f"unsupported: {suffix or 'no extension'}"


def build(root: Path) -> Dict[str, int]:
    """Write one text file per record into the hidden index folder; return counts per extraction method."""
    target = index_dir(root)
    if target.exists():
        shutil.rmtree(target)
    target.mkdir()
    counts: Dict[str, int] = {}
    report = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if not is_record(path) or any(part.startswith(".") for part in rel.parts) or path.name.lower() in CATALOG_NAMES:
            continue
        text, method = extract(path)
        counts[method] = counts.get(method, 0) + 1
        report.append(f"{rel.as_posix()}\t{method}")
        if text:
            out = target / (rel.as_posix() + ".txt")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(f"SOURCE: {rel.as_posix()}\nMETHOD: {method}\n\n{text}\n", encoding="utf-8")
    (target / REPORT).write_text("\n".join(report) + "\n", encoding="utf-8")
    return counts


def drop(root: Path) -> None:
    if index_dir(root).exists():
        shutil.rmtree(index_dir(root))


def _hit(rel: str, body: str, first_term: str) -> Hit:
    pos = body.lower().find(first_term)
    pages = [(m.start(), int(m.group(1))) for m in SECTION.finditer(body)]
    page = max((n for start, n in pages if start <= pos), default=0)
    snippet = " ".join(body[max(0, pos - SNIPPET):pos + len(first_term) + SNIPPET].split())
    return Hit(rel, page, snippet)


def search(path, query: str) -> List[Hit]:
    """Documents of a closed collection that contain all query terms (case-insensitive)."""
    root = closed_root(full_path(path))
    if root is None or not index_dir(root).exists():
        raise FilingError(f"no full-text index: {path} is not a closed collection")
    terms = [t.lower() for t in query.split()]
    hits = []
    for txt in sorted(index_dir(root).rglob("*.txt")):
        body = txt.read_text(encoding="utf-8").split("\n\n", 1)[-1]
        if terms and all(t in body.lower() for t in terms):
            hits.append(_hit(txt.relative_to(index_dir(root)).as_posix()[:-len(".txt")], body, terms[0]))
    return hits
