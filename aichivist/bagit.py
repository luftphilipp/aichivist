"""Export a closed collection as a BagIt 1.0 bag (RFC 8493, Library of Congress) and validate bags.

The bag is a self-describing archival package: payload in data/, SHA-256 manifests, bag-info metadata. Any
BagIt tool (e.g. bagit-python, Bagger) can validate it – no aichivist needed in the future.
"""
import shutil
from datetime import date
from pathlib import Path
from typing import Dict, List

from . import __version__, journal, lifecycle
from .checksums import digest, manifest
from .config import full_path
from .fileops import FilingError

BAGIT_TXT = "BagIt-Version: 1.0\nTag-File-Character-Encoding: UTF-8\n"
PAYLOAD_MANIFEST = "manifest-sha256.txt"
TAG_MANIFEST = "tagmanifest-sha256.txt"
TAG_FILES = ("bagit.txt", "bag-info.txt", PAYLOAD_MANIFEST)


def encode(path: str) -> str:
    """Only CR/LF are encoded, as in the reference implementation bagit-python. RFC 8493 also asks for "%" → "%25",
    but bagit-python does not decode it, so such bags would fail validation there; interoperability wins."""
    return path.replace("\r", "%0D").replace("\n", "%0A")


def decode(path: str) -> str:
    return path.replace("%0A", "\n").replace("%0D", "\r")


def _write_manifest(path: Path, entries: Dict[str, str]) -> None:
    path.write_text("".join(f"{h}  {encode(rel)}\n" for rel, h in sorted(entries.items())), encoding="utf-8")


def _read_manifest(path: Path) -> Dict[str, str]:
    entries = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            checksum, rel = line.split(maxsplit=1)
            entries[decode(rel.strip())] = checksum
    return entries


def _copy_payload(root: Path, dest: Path, recorded: Dict[str, str]) -> Dict[str, str]:
    payload = {}
    for rel, checksum in recorded.items():
        target = dest / "data" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, target)
        if digest(target) != checksum:
            raise FilingError(f"copy of {rel} does not match the fixity manifest; export aborted")
        payload[f"data/{rel}"] = checksum
    return payload


def export(area, dest) -> Path:
    info = lifecycle.status(area)
    if info.state != "closed":
        raise FilingError(f"only closed collections can be exported as a bag: {area}")
    root, dest = info.root, full_path(dest)
    if dest.exists():
        raise FilingError(f"target exists, nothing overwritten: {dest}")
    changes = [f"{kind} {rel}" for kind, items in lifecycle.verify(root).items() for rel in items]
    if changes:
        raise FilingError(f"{root} changed since it was closed ({', '.join(changes[:5])}); run `aichivist verify`")
    recorded = lifecycle.recorded_manifest(root)
    try:
        payload = _copy_payload(root, dest, recorded)
    except BaseException:
        shutil.rmtree(dest, ignore_errors=True)  # no half-written bag
        raise
    (dest / "bagit.txt").write_text(BAGIT_TXT, encoding="utf-8")
    _write_manifest(dest / PAYLOAD_MANIFEST, payload)
    total = sum((root / rel).stat().st_size for rel in recorded)
    (dest / "bag-info.txt").write_text(
        f"Bagging-Date: {date.today().isoformat()}\n"
        f"Payload-Oxum: {total}.{len(recorded)}\n"
        f"External-Identifier: {root.name}\n"
        f"External-Description: {' '.join((info.note or 'closed collection').split())}\n"
        f"Closed-At: {info.closed_at}\n"
        f"Bag-Software-Agent: aichivist {__version__}\n", encoding="utf-8")
    _write_manifest(dest / TAG_MANIFEST, {name: digest(dest / name) for name in TAG_FILES})
    journal.write(root, dest, "export_bag")
    return dest


def validate(bag) -> List[str]:
    """Problems found in a bag; an empty list means the bag is complete and intact."""
    bag = full_path(bag)
    if not (bag / "bagit.txt").exists() or not (bag / PAYLOAD_MANIFEST).exists():
        return ["not a bag: bagit.txt or manifest-sha256.txt missing"]
    problems = []
    if (bag / TAG_MANIFEST).exists():
        for name, checksum in _read_manifest(bag / TAG_MANIFEST).items():
            if not (bag / name).exists() or digest(bag / name) != checksum:
                problems.append(f"tag file changed: {name}")
    recorded = _read_manifest(bag / PAYLOAD_MANIFEST)
    present = {f"data/{rel}": h for rel, h in manifest(bag / "data").items()} if (bag / "data").exists() else {}
    problems += [f"changed: {rel}" for rel in sorted(recorded) if rel in present and present[rel] != recorded[rel]]
    problems += [f"missing: {rel}" for rel in sorted(recorded) if rel not in present]
    problems += [f"not in manifest: {rel}" for rel in sorted(present) if rel not in recorded]
    return problems
