"""Claude Code PreToolUse hook: block raw changes in protected areas so every change goes through aichivist.

Blocked in protected areas: moving, renaming, deleting (mv, rm, find -delete, xargs rm, Python one-liners,
PowerShell), copying files *into* them (cp, rsync, tee …) and overwriting redirects (`> file`). Reading and copying
*out* are allowed. This is a safety net for the usual ways an agent touches files, not a sandbox.
"""
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from . import protect

SHELL_TOOLS = {"Bash", "PowerShell"}
DESTRUCTIVE_COMMANDS = {"mv", "rm", "rmdir", "unlink", "shred", "srm", "trash", "del", "rd", "move", "erase"}
DESTRUCTIVE_CALLS = ("os.remove(", "os.unlink(", "os.rename(", "os.replace(", "os.rmdir(", "shutil.move(",
                     "shutil.rmtree(", ".unlink(", ".rename(", ".replace(", ".rmdir(", "-delete",
                     "--remove-source-files", "Remove-Item", "Move-Item", "Rename-Item")
WRITE_INTO = {"cp", "rsync", "install", "ditto", "tee", "copy", "xcopy", "robocopy", "copy-item"}
WRAPPERS = {"sudo", "command", "env", "nohup", "time"}
COMMAND_SPLIT = re.compile(r"&&|\|\||;|\n")
PIPE_SPLIT = re.compile(r"(?<!\|)\|(?!\|)")
REDIRECT = re.compile(r"(?<![<>&\d])>>?\s*(\"[^\"]+\"|'[^']+'|\S+)")
BOUNDARY = r"(?=$|[/\\'\"\s])"


def _forms(root: Path) -> List[str]:
    """Ways a path can be written in a shell command."""
    forms = {str(root), root.as_posix(), str(root).replace(" ", "\\ ")}
    try:
        rel = root.relative_to(Path.home()).as_posix()
        forms |= {f"~/{rel}", f"~/{rel}".replace(" ", "\\ "), f"$HOME/{rel}"}
    except ValueError:
        pass
    return sorted(forms, key=len, reverse=True)


def _mentions(text: str, roots: Iterable[Path]) -> Optional[Path]:
    return next((r for r in roots if any(re.search(re.escape(f) + BOUNDARY, text) for f in _forms(r))), None)


def _program_and_args(part: str) -> Tuple[str, List[str]]:
    try:
        tokens = shlex.split(part)
    except ValueError:
        tokens = part.split()
    tokens = [t for t in tokens if t not in WRAPPERS and "=" not in t.split("/")[0]]
    return (Path(tokens[0]).name.lower(), tokens[1:]) if tokens else ("", [])


def _destructive(part: str) -> bool:
    program, args = _program_and_args(part)
    if program == "aichivist":
        return False
    if program in DESTRUCTIVE_COMMANDS or any(call in part for call in DESTRUCTIVE_CALLS):
        return True
    return program == "xargs" and any(Path(a).name.lower() in DESTRUCTIVE_COMMANDS for a in args)


def _writes_into(part: str, roots: List[Path]) -> Optional[Path]:
    program, args = _program_and_args(part)
    if program not in WRITE_INTO:
        return None
    targets = [a for a in args if not a.startswith("-")]
    targets = targets if program == "tee" else targets[-1:]  # cp/rsync: last argument is the destination
    return next((root for t in targets if (root := _mentions(t, roots))), None)


def _redirects_into(part: str, roots: List[Path]) -> Optional[Path]:
    return next((root for m in REDIRECT.finditer(part) if (root := _mentions(m.group(1).strip("'\""), roots))), None)


def check_command(command: str, protected: Iterable[Path]) -> Optional[str]:
    """A message explaining the block, or None if the command may run."""
    roots = list(protected)
    for single in COMMAND_SPLIT.split(command):
        parts = PIPE_SPLIT.split(single)
        hit = _mentions(single, roots) if any(_destructive(p) for p in parts) else None
        for part in parts:
            if _program_and_args(part)[0] != "aichivist":
                hit = hit or _writes_into(part, roots) or _redirects_into(part, roots)
        if hit:
            return (f"aichivist guard: {hit} is a protected filing area. Move, rename, delete or add files there "
                    f"only with `aichivist mv` / `aichivist trash` or a filing plan, so every step is logged "
                    f"and can be undone.")
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if payload.get("tool_name") not in SHELL_TOOLS:
        return 0
    message = check_command(payload.get("tool_input", {}).get("command", ""), protect.listed())
    if message:
        print(message, file=sys.stderr)
        return 2  # Claude Code: block the tool call and show the message to the agent
    return 0
