"""Program data: notice before a move that a program depends on a path, so programs keep working afterwards.

A file is program data when it lies in a place programs manage (Library, AppData, Program Files, ~/.config …),
belongs to a program library or project (Photos library, Lightroom catalog, Obsidian vault, Steam, code project …),
is the target of a link or shortcut, or is open in a running program. aichivist then refuses to move it: the person
either adjusts the program first (`--app-data`), or moves it with `--leave-link` (plan mark `link`) – a link at the
old place points to the new one, so the program finds its files as before.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional, Tuple

from .config import full_path
from .i18n import t
from .inventory import PROJECT_MARKERS

LIBRARY_SUFFIXES = {
    ".app": "program", ".photoslibrary": "Photos library", ".musiclibrary": "Music library",
    ".tvlibrary": "TV library", ".lrcat": "Lightroom catalog", ".lrdata": "Lightroom catalog",
    ".fcpbundle": "Final Cut library", ".logicx": "Logic project", ".band": "GarageBand project",
    ".aplibrary": "Aperture library", ".vmwarevm": "virtual machine", ".pvm": "virtual machine",
    ".vbox": "virtual machine", ".utm": "virtual machine",
}
FOLDER_MARKERS = {
    ".obsidian": "Obsidian vault", "zotero.sqlite": "Zotero library", "metadata.db": "Calibre library",
    "collection.anki2": "Anki profile", "steamapps": "Steam library", "prefs.js": "Firefox/Thunderbird profile",
    ".minecraft": "Minecraft folder", "node_modules": "code project", "iTunes Library.itl": "iTunes library",
    **{marker: "code project" for marker in PROJECT_MARKERS},
}
LINK_DEPTH = 3          # how deep below the home folder links and shortcuts are looked for
SHORTCUT_MAX = 65536    # Windows .lnk files are small; bigger files are not shortcuts
LSOF_TIMEOUT = 20       # seconds for listing the files open in running programs
SHOWN_PROGRAMS = 3      # programs named per open file


class Context(NamedTuple):
    """Collected once per run: links/shortcuts (place → what they point to) and files open in programs."""
    links: List[Tuple[Path, str]]
    open_files: Dict[str, str]


def managed_places() -> List[Path]:
    """Folders that belong to programs or the system, per operating system."""
    home = Path.home()
    if sys.platform == "win32":
        names = ("APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "ProgramFiles", "ProgramFiles(x86)", "SystemRoot")
        return [Path(os.environ[n]) for n in names if os.environ.get(n)]
    if sys.platform == "darwin":
        return [home / "Library", Path("/Library"), Path("/Applications"), Path("/System"), Path("/usr"),
                Path("/opt")]
    return [home / ".config", home / ".local", home / ".var", home / "snap", Path("/usr"), Path("/opt"),
            Path("/etc"), Path("/var/lib")]


def user_places() -> List[Path]:
    """The person's own cloud folders, even though they lie inside program folders (iCloud Drive in ~/Library …)."""
    home = Path.home()
    return [home / "Library" / "Mobile Documents" / "com~apple~CloudDocs", home / "Library" / "CloudStorage"]


def _inside(path: Path, folder: Path) -> bool:
    return path == folder or folder in path.parents


def place_risk(path: Path) -> Optional[str]:
    """Is the path in a folder that programs manage? Temporary folders are not counted."""
    if any(_inside(path, p) for p in [Path(tempfile.gettempdir()).resolve(), *user_places()]):
        return None
    for place in managed_places():
        if _inside(path, place):
            return t("in the program folder {place}", place=place)
    home = Path.home()
    if _inside(path, home) and path != home:
        parts = path.relative_to(home).parts  # programs keep hidden folders directly in the home folder (~/.config);
        if len(parts) > 1 and parts[0].startswith("."):  # hidden folders deeper down belong to the person
            return t("in the hidden program folder {place}", place=home / parts[0])
    return None


def kind_of(folder: Path, names: Iterable[str]) -> Optional[str]:
    """Program library or project, judged from the folder's name and its entry names (no extra disk access)."""
    if folder.suffix.lower() in LIBRARY_SUFFIXES:
        return LIBRARY_SUFFIXES[folder.suffix.lower()]
    present = set(names)
    return next((kind for marker, kind in FOLDER_MARKERS.items() if marker in present), None)


def _kind(folder: Path) -> Optional[str]:
    if folder.suffix.lower() in LIBRARY_SUFFIXES:
        return LIBRARY_SUFFIXES[folder.suffix.lower()]
    try:
        if not folder.is_dir():
            return None
        return next((kind for marker, kind in FOLDER_MARKERS.items() if (folder / marker).exists()), None)
    except OSError:  # a folder that cannot be read (owned by another user) is not judged
        return None


def library_risk(path: Path, look_inside: bool = True) -> Optional[str]:
    """Is the path a program library or project, part of one, or (with `look_inside`) does it contain one?"""
    for folder in [path, *path.parents]:
        kind = _kind(folder)
        if kind:
            return t("is a {kind}", kind=t(kind)) if folder == path else t("part of a {kind} ({folder})",
                                                                          kind=t(kind), folder=folder)
    if look_inside and path.is_dir():
        for dirpath, dirnames, _ in os.walk(path):
            for d in dirnames:
                kind = _kind(Path(dirpath) / d)
                if kind:
                    return t("contains a {kind} ({folder})", kind=t(kind), folder=Path(dirpath) / d)
    return None


def _shortcut_text(lnk: Path) -> str:
    """Text of a Windows shortcut; its target path is searched in it, no shortcut parser needed."""
    try:
        if lnk.stat().st_size > SHORTCUT_MAX:
            return ""
        data = lnk.read_bytes()
    except OSError:
        return ""
    return "\n".join((data.decode("latin-1"), data.decode("utf-16-le", "ignore"),
                      data[1:].decode("utf-16-le", "ignore")))


def find_links(roots: Iterable[Path], depth: int = LINK_DEPTH) -> List[Tuple[Path, str]]:
    """Symbolic links (resolved target) and Windows shortcuts (their text) below the roots, skipping program folders."""
    found: List[Tuple[Path, str]] = []
    places = managed_places()
    for root in roots:
        if not root.is_dir():
            continue
        base = len(root.parts)
        for dirpath, dirnames, filenames in os.walk(root):
            folder = Path(dirpath)
            for name in dirnames + filenames:
                entry = folder / name
                if entry.is_symlink():
                    found.append((entry, os.path.realpath(entry)))
                elif name.lower().endswith(".lnk"):
                    found.append((entry, _shortcut_text(entry)))
            if len(folder.parts) - base >= depth:
                dirnames.clear()
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and not (folder / d).is_symlink()
                           and not (place_risk(folder / d) and any(_inside(folder / d, p) for p in places))]
    return found


def open_files() -> Dict[str, str]:
    """Files open in the person's running programs (path → program), via lsof where it exists."""
    lsof = shutil.which("lsof")
    if not lsof or not hasattr(os, "getuid"):
        return {}  # Windows itself refuses to move files that are open
    try:
        out = subprocess.run([lsof, "-w", "-n", "-u", str(os.getuid()), "-F", "cn"], capture_output=True,
                             text=True, errors="replace", timeout=LSOF_TIMEOUT).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    files: Dict[str, str] = {}
    program = ""
    for line in out.splitlines():
        if line.startswith("c"):
            program = line[1:]
        elif line.startswith("n/"):
            files.setdefault(line[1:], program)
    return files


def context(roots: Optional[Iterable[Path]] = None) -> Context:
    """Links below the home folder (and the Windows start menu) plus open files, collected once."""
    if roots is None:
        roots = [Path.home()]
        if sys.platform == "win32" and os.environ.get("APPDATA"):
            roots.append(Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu")
    return Context(find_links(roots), open_files())


def _points_to(link: Path, target: str, path: Path, real: str) -> bool:
    if link.suffix.lower() == ".lnk" and not link.is_symlink():
        return str(path).lower() in target.lower()
    return target == real or target.startswith(real + os.sep)


def risks(path, ctx: Context) -> List[str]:
    """Reasons why moving or deleting `path` may stop a program from working. Empty list: safe to move."""
    path = full_path(path)
    real = os.path.realpath(path)
    found = [r for r in (place_risk(path), library_risk(path)) if r]
    found += [t("the link {link} points to it", link=link) for link, target in ctx.links
              if link != path and _points_to(link, target, path, real)]
    in_use = sorted({prog for f, prog in ctx.open_files.items() if f == real or f.startswith(real + os.sep)})
    if in_use:
        more = t(" and {n} more", n=len(in_use) - SHOWN_PROGRAMS) if len(in_use) > SHOWN_PROGRAMS else ""
        found.append(t("open in {programs}{more} – close it first", programs=", ".join(in_use[:SHOWN_PROGRAMS]),
                       more=more))
    return found


def target_risk(target) -> Optional[str]:
    """Filing into a program folder or library would hand records over to a program. Other things in the target
    folder do not matter: a project next to the target is not touched."""
    folder = full_path(target).parent
    return place_risk(folder) or library_risk(folder, look_inside=False)


def leave_link(old: Path, new: Path) -> None:
    """Put a link at the old place that points to the new one, so programs find the files as before.
    Where symbolic links are not allowed (Windows without Developer Mode): a junction for folders, a hard link for
    files (same drive only) – neither needs admin rights."""
    try:
        os.symlink(new, old, target_is_directory=new.is_dir())
        return
    except OSError:
        if new.is_dir() and sys.platform != "win32":
            raise
    if new.is_dir():
        done = subprocess.run(["cmd", "/c", "mklink", "/J", str(old), str(new)], capture_output=True, text=True)
        if done.returncode != 0:
            raise OSError(done.stderr.strip() or "mklink /J failed")
    else:
        os.link(new, old)


def is_link_to(old: Path, new: Path) -> bool:
    """Is `old` a link left behind by leave_link that leads to `new`?"""
    if not new.exists() or not (old.is_symlink() or old.exists()):
        return False
    if old.is_symlink() or (old.is_dir() and sys.platform == "win32"):
        return old != new and os.path.realpath(old) == os.path.realpath(new)
    return old.is_file() and new.is_file() and os.path.samefile(old, new)


def remove_link(old: Path) -> None:
    """Remove only the link itself – never what it points to."""
    try:
        old.unlink()
    except OSError:
        os.rmdir(old)  # directory symlinks and junctions on Windows; fails safely on a real, non-empty folder
