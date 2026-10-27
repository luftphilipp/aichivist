"""Protected areas: folders in which the agent must not move or delete files except through aichivist."""
from pathlib import Path
from typing import List

from . import config, journal
from .config import full_path


def _file() -> Path:
    return config.home_dir() / "protected.txt"


def listed() -> List[Path]:
    if not _file().exists():
        return []
    return [Path(line) for line in _file().read_text(encoding="utf-8").splitlines() if line.strip()]


def _save(paths: List[Path]) -> None:
    _file().parent.mkdir(parents=True, exist_ok=True)
    _file().write_text("".join(f"{p}\n" for p in paths), encoding="utf-8")


def add(folder) -> Path:
    path = full_path(folder)
    if path not in listed():
        _save(listed() + [path])
        journal.write("", path, "protect")
    return path


def remove(folder) -> None:
    path = full_path(folder)
    if path in listed():
        _save([p for p in listed() if p != path])
        journal.write(path, "", "unprotect")
