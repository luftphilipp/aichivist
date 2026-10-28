"""Read a document and prefill what a person would write: date, issuer, kind, summary, keywords, a suggested name.

Deterministic and local – a starting point the agent (or person) checks and improves, marked with "◇" in catalogs.
"""
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import fulltext

DATE_ISO = re.compile(r"\b(20\d{2}|19\d{2})-(\d{2})-(\d{2})\b")
DATE_DOTTED = re.compile(r"\b(\d{1,2})\.\s?(\d{1,2})\.\s?(20\d{2}|19\d{2})\b")
MONTHS = {m: i for i, names in enumerate([
    ("january", "januar", "janvier"), ("february", "februar", "février"), ("march", "märz", "mars"),
    ("april", "avril"), ("may", "mai"), ("june", "juni", "juin"), ("july", "juli", "juillet"),
    ("august", "août"), ("september", "septembre"), ("october", "oktober", "octobre"),
    ("november", "novembre"), ("december", "dezember", "décembre")], 1) for m in names}
DATE_WORDS = re.compile(r"\b(\d{1,2})\.?\s+([A-Za-zäéû]+)\s+(20\d{2}|19\d{2})\b")
KINDS = [  # first match wins; (English label, German label, words that indicate it)
    ("Invoice", "Rechnung", ("rechnung", "invoice", "facture", "fattura")),
    ("Reminder", "Mahnung", ("mahnung", "reminder", "rappel")),
    ("Policy", "Police", ("police", "policy", "versicherungsschein")),
    ("Statement", "Kontoauszug", ("kontoauszug", "statement", "auszug", "relevé")),
    ("Contract", "Vertrag", ("vertrag", "contract", "contrat", "agreement")),
    ("Certificate", "Zeugnis", ("zeugnis", "certificate", "diplom", "diploma", "bestätigung", "attestation")),
    ("Decision", "Verfügung", ("verfügung", "decision", "bescheid")),
    ("Receipt", "Quittung", ("quittung", "receipt", "beleg")),
    ("Quote", "Offerte", ("offerte", "angebot", "quote", "offer")),
    ("Letter", "Brief", ("sehr geehrte", "dear ", "madame", "monsieur")),
]
BIRTH = re.compile(r"geb\.|geboren|geburt|birth|né le|née le|date of birth", re.IGNORECASE)
MAX_AGE_GAP = 15  # years
BIRTH_WINDOW = 40  # characters before a date that are checked for a birth-date label
STREET = re.compile(r"(strasse|straße|str|gasse|weg|platz|rain|allee|ring|road|street|avenue|rue)$", re.IGNORECASE)
GERMAN_HINTS = (" und ", " der ", " die ", " das ", " mit ", " für ", " ihre ", " sehr geehrte", " rechnung",
                " betrag", " bestellung", " inkl", " mwst", " datum")
SALUTATION = re.compile(r"\b(?:Herrn?|Frau|Mr\.?|Mrs\.?|Ms\.?)\s+([A-ZÄÖÜ][\wäöüé-]+)(?:\s+([A-ZÄÖÜ][\wäöüé-]+))?")
DOMAIN = re.compile(r"\b(?:www\.)?([a-z][a-z0-9-]{2,30})\.(?:ch|de|at|com|net|org|eu|fr|it)\b", re.IGNORECASE)
NOISE_WORDS = (
    "mwst inkl exkl total betrag summe seite page datum date nummer kunde kunden rechnungsnummer telefon email "
    "strasse postfach schweiz switzerland iban konto bestellung versichert versicherte store kundennummer "
    "sehr geehrte geehrter dear"
)
NOISE = frozenset(NOISE_WORDS.split())
LEGAL_FORMS = r"AG|GmbH|SA|Sàrl|Ltd|Inc|LLC|KG|eG|Versicherung(?:en)?|Bank|Kantonalbank"
COMPANY = re.compile(rf"\b((?:[A-ZÄÖÜ][\w&\-]*\.?\s){{1,4}}(?:{LEGAL_FORMS}))\b")  # 1–4 capitalised words
STOP_WORDS = (
    "der die das und oder ein eine einer eines für mit von zu im in am an auf ist sind sie ihr ihre wir uns "
    "the a an and or of to in on for with from by is are be this that your you we our le la les de des du et "
    "pour une un est sont dem den bei aus als auch nicht nur noch sowie per vom zum zur bis wird werden hat haben "
    "chf eur"
)
STOP = frozenset(STOP_WORDS.split())
KEYWORDS = 5
SUBJECT_WORDS = 3  # at most this many words of subject in a suggested name
SUMMARY_CHARS = 120


def find_date(text: str) -> Optional[str]:
    candidates = []
    for m in DATE_ISO.finditer(text):
        candidates.append((m.start(), f"{m.group(1)}-{m.group(2)}-{m.group(3)}"))
    for m in DATE_DOTTED.finditer(text):
        candidates.append((m.start(), f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"))
    for m in DATE_WORDS.finditer(text):
        month = MONTHS.get(m.group(2).lower())
        if month:
            candidates.append((m.start(), f"{m.group(3)}-{month:02d}-{int(m.group(1)):02d}"))
    valid = [(pos, d) for pos, d in candidates if 1 <= int(d[5:7]) <= 12 and 1 <= int(d[8:10]) <= 31
             and not BIRTH.search(text[max(0, pos - BIRTH_WINDOW):pos])]  # birth dates are not document dates
    if not valid:
        return None
    newest = max(int(d[:4]) for _, d in valid)  # dates far older than the newest one are birth dates and the like
    recent = [(pos, d) for pos, d in valid if int(d[:4]) >= newest - MAX_AGE_GAP] or valid
    return min(recent)[1]  # the first (recent) date in the document is usually the document date


def is_german(text: str) -> bool:
    lower = f" {text.lower()} "
    return sum(lower.count(h) for h in GERMAN_HINTS) >= 3


def find_kind(text: str) -> Optional[str]:
    """Kind of document, in the document's language (German or English)."""
    lower, german = text.lower(), is_german(text)
    return next(((de if german else en) for en, de, words in KINDS if any(w in lower for w in words)), None)


def find_issuer(text: str) -> Optional[str]:
    """A company name with legal form (… AG, … GmbH), else the name of the first web domain (example-shop.ch)."""
    match = COMPANY.search(text[:2000])
    if match:
        words = match.group(1).split()
        while len(words) > 2 and words[0].lower() in STOP:
            words = words[1:]  # "Die Schweizerische Mobiliar AG" → "Schweizerische Mobiliar AG"
        return " ".join(words)
    domain = DOMAIN.search(text[:3000])
    return domain.group(1) if domain else None


def keywords(text: str, n: int = KEYWORDS) -> List[str]:
    words = [w.lower() for w in re.findall(r"[A-Za-zÄÖÜäöüéèàç]{4,}", text)]
    return [w for w, _ in Counter(w for w in words if w not in STOP).most_common(n)]


def summary(text: str) -> str:
    for line in (" ".join(part.split()) for part in re.split(r"[\n.]", text)):
        if len(line) >= 20 and not line.startswith("==="):
            return line[:SUMMARY_CHARS]
    return ""


def subject_after_kind(text: str, skip: set) -> str:
    """The words right after the kind word ("Policy basic insurance" → "basic insurance"), up to SUBJECT_WORDS,
    stopping at punctuation, numbers, stop words and names."""
    lower = text.lower()
    for _, _, indicators in KINDS:
        for word in indicators:
            at = lower.find(word)
            if at < 0 or not word.isalpha():
                continue
            found: List[str] = []
            tokens = re.split(r"[ \t]+", text[at + len(word):].lstrip())
            while tokens and tokens[0].lower() in STOP and len(tokens) > 1:
                tokens = tokens[1:]  # "Rechnung für das Abo" → start at "Abo"
            for token in tokens[:SUBJECT_WORDS]:
                clean = token.strip()
                if not re.fullmatch(r"[A-Za-zÄÖÜäöüéèàç]{3,}", clean) or clean.lower() in STOP | NOISE | skip \
                        or _in_address(clean, text):
                    break
                found.append(clean)
            return " ".join(found)
    return ""


def _in_address(word: str, text: str) -> bool:
    """Words next to a postal code (4–5 digits) are usually a place name in an address block."""
    if STREET.search(word):
        return True
    return re.search(rf"\b\d{{4,5}}\s+{re.escape(word)}\b", text, re.IGNORECASE) is not None


def suggest(path: Path, text: Optional[str] = None) -> Dict[str, Any]:
    """Prefilled description and a name following `[YYYY-MM-DD ]Issuer Kind Subject.ext`."""
    if text is None:
        text, _ = fulltext.extract(path)
    date, issuer, kind = find_date(text), find_issuer(text), find_kind(text)
    words = keywords(text, n=KEYWORDS * 2)
    issuer_words = set((issuer or "").lower().split())
    people = {n.lower() for m in SALUTATION.finditer(text) for n in m.groups() if n}  # recipients, not subjects
    kind_words = {w for _, _, ws in KINDS for w in ws}
    subject = subject_after_kind(text, issuer_words | people | kind_words) or next(
        (w.capitalize() for w in words
         if w not in issuer_words | people | kind_words and w not in NOISE and not _in_address(w, text)), "")
    words = words[:KEYWORDS]
    parts = [p for p in (date, issuer, kind, subject) if p]
    confident = bool(issuer or kind)  # without issuer and kind, date + one keyword is a guess (calendars, tables)
    name = " ".join(parts) + path.suffix.lower() if parts and confident else path.name
    return {"date": date, "issuer": issuer, "kind": kind, "summary": summary(text), "keywords": words,
            "suggested_name": name, "confident": confident, "has_text": bool(text.strip())}


def rows(files) -> List[Dict[str, Any]]:
    """One compact suggestion per file: enough to file most documents without reading them in full."""
    found = []
    for file in files:
        s = suggest(file)
        found.append({"file": file.name, "folder": str(file.parent), "date": s["date"], "issuer": s["issuer"],
                      "kind": s["kind"], "suggested_name": s["suggested_name"], "confident": s["confident"]})
    return found


def visible_files(paths) -> List[Path]:
    """The given files, plus the visible files directly inside the given folders."""
    found: List[Path] = []
    for path in paths:
        entries = sorted(path.iterdir()) if path.is_dir() else [path]
        found += [e for e in entries if e.is_file() and not e.name.startswith(".")]
    return found
