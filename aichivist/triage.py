"""One look at an inbox: for every entry what it is and what to do – read only, nothing is changed.

Categories: document (with a suggested name), temporary (a screenshot without a document), sensitive (shows a
secret), downloading / stalled, installer, archive, film, episode, personal video, photo.
"""
from pathlib import Path
from typing import Any, Dict, List

from . import describe, inbox
from .config import full_path
from .photos import IMAGES

HINTS = {
    "document": "file it (check the suggested name)",
    "temporary": "screenshot without a document – propose the trash",
    "sensitive": "shows a secret – save it in a password manager, then propose the trash",
    "downloading": "still downloading – leave it",
    "stalled": "download stopped – restart or cancel it in the browser",
    "installer": "installer – list only; propose the trash once installed",
    "archive": "archive – list only, contents are not sorted",
    "film": "film – not a document; file it with your media rules",
    "episode": "series episode – not a document; file it with your media rules",
    "personal video": "personal video – use `aichivist photos`",
    "photo": "photo – use `aichivist photos`",
}


def _row(path: Path, category: str, **extra: Any) -> Dict[str, Any]:
    return {"file": path.name, "category": category, "hint": HINTS[category], **extra}


def classify(path: Path) -> Dict[str, Any]:
    if inbox.is_partial(path):
        return _row(path, inbox.download_state(path))
    kind = inbox.package_kind(path) or inbox.media_kind(path)
    if kind:
        return _row(path, kind)
    s = describe.suggest(path)
    if s["sensitive"]:
        return _row(path, "sensitive", secrets=s["sensitive"])
    if s.get("temporary"):
        return _row(path, "temporary", summary=s["summary"])
    if not s["has_text"] and path.suffix.lower() in IMAGES:
        return _row(path, "photo")
    return _row(path, "document", suggested_name=s["suggested_name"], confident=s["confident"])


def run(folder) -> List[Dict[str, Any]]:
    """Files directly inside the folder, plus running downloads and app bundles; other subfolders are left out."""
    root = full_path(folder)
    entries = [e for e in sorted(root.iterdir()) if not e.name.startswith(".")]
    return [classify(e) for e in entries
            if e.is_file() or inbox.is_partial(e) or e.suffix.lower() == ".app"]
