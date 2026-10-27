"""Messages for people in their language: German or English (default), from AICHIVIST_LANG or the system language.

The English text is the key: `t("{n} rows approved", n=3)` → "3 Zeilen freigegeben" on a German system.
Missing translations fall back to English, so a new message never breaks anything.
"""
import locale
import os

from .lang_de import GERMAN, GERMAN_NOUNS


def _setting() -> str:
    """The chosen or system language tag, e.g. "de_CH", "en_US", "German_Switzerland"."""
    chosen = os.environ.get("AICHIVIST_LANG", "")
    if chosen:
        return chosen
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(name, "")
        if value and value not in ("C", "POSIX") and not value.startswith("C."):
            return value
    try:
        return locale.getlocale()[0] or ""
    except ValueError:
        return ""


def language() -> str:
    return "de" if _setting().lower().startswith(("de", "german")) else "en"


def swiss() -> bool:
    """Swiss German writes "ss" instead of "ß"."""
    tag = _setting().lower().replace("-", "_")
    return tag.endswith("_ch") or "_ch." in tag or "switzerland" in tag


def t(text: str, **values) -> str:
    if language() != "de":
        return text.format(**values) if values else text
    template = GERMAN.get(text, text)
    if swiss():
        template = template.replace("ß", "ss")
    return template.format(**values) if values else template


def count(n: int, noun: str) -> str:
    """"3 files" / "1 file" – or "3 Dateien" / "1 Datei"."""
    if language() == "de" and noun in GERMAN_NOUNS:
        one, many = GERMAN_NOUNS[noun]
        return f"{n:,} {one if n == 1 else many}".replace(",", " ")
    return f"{n:,} {noun}{'' if n == 1 else 's'}"
