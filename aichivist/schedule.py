"""Daily reminder with one command: `aichivist watch ~/Downloads --install [--at 09:00]`, removed with `--uninstall`.

Uses what each system already has: launchd on macOS, a systemd user timer on Linux, the Task Scheduler on Windows.
The scheduled run is `aichivist watch …`, which only speaks up when enough files wait.
"""
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, NamedTuple, Optional, Sequence

from .config import full_path

LABEL = "io.github.luftphilipp.aichivist.watch"
UNIT = "aichivist-watch"
TASK = "aichivist-watch"
TASK_COMMAND_MAX = 261  # Windows limits the command of a scheduled task to this many characters


class Job(NamedTuple):
    files: Dict[Path, str]       # files to write
    commands: List[List[str]]    # commands that activate the schedule


def watch_command(inboxes: Sequence, threshold: int) -> List[str]:
    python = Path(sys.executable)
    windowless = python.with_name("pythonw.exe")  # no console window popping up every morning on Windows
    exe = windowless if sys.platform == "win32" and windowless.exists() else python
    return [str(exe), "-m", "aichivist", "watch", *[str(full_path(i)) for i in inboxes], "--threshold", str(threshold)]


def _plist(command: List[str], hour: int, minute: int) -> str:
    args = "".join(f"<string>{a.replace('&', '&amp;').replace('<', '&lt;')}</string>" for a in command)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            f'<plist version="1.0"><dict><key>Label</key><string>{LABEL}</string>'
            f"<key>ProgramArguments</key><array>{args}</array>"
            f"<key>StartCalendarInterval</key><dict><key>Hour</key><integer>{hour}</integer>"
            f"<key>Minute</key><integer>{minute}</integer></dict></dict></plist>\n")


def _quoted(command: List[str]) -> str:
    return " ".join(f'"{a}"' if " " in a else a for a in command)


def job(inboxes: Sequence, threshold: int, at: str, platform: str = sys.platform) -> Job:
    match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", at)
    if not match:
        raise ValueError(f"time '{at}' is not HH:MM, e.g. 09:00")
    hour, minute = int(match.group(1)), int(match.group(2))
    command = watch_command(inboxes, threshold)
    home = Path.home()
    if platform == "darwin":
        plist = home / "Library" / "LaunchAgents" / f"{LABEL}.plist"
        uid = str(os.getuid()) if hasattr(os, "getuid") else "0"
        return Job({plist: _plist(command, hour, minute)},
                   [["launchctl", "bootout", f"gui/{uid}", str(plist)],
                    ["launchctl", "bootstrap", f"gui/{uid}", str(plist)]])
    if platform == "win32":
        task = _quoted(command)
        if len(task) > TASK_COMMAND_MAX:
            raise ValueError("the reminder command is too long for the Task Scheduler – use fewer or shorter inboxes")
        return Job({}, [["schtasks", "/Create", "/F", "/SC", "DAILY", "/TN", TASK, "/TR", task,
                         "/ST", f"{hour:02d}:{minute:02d}"]])
    units = home / ".config" / "systemd" / "user"
    return Job({units / f"{UNIT}.service": f"[Unit]\nDescription=aichivist reminder\n\n[Service]\nType=oneshot\n"
                                           f"ExecStart={_quoted(command)}\n",
                units / f"{UNIT}.timer": f"[Unit]\nDescription=aichivist daily reminder\n\n[Timer]\n"
                                         f"OnCalendar=*-*-* {hour:02d}:{minute:02d}:00\nPersistent=true\n\n"
                                         "[Install]\nWantedBy=timers.target\n"},
               [["systemctl", "--user", "daemon-reload"],
                ["systemctl", "--user", "enable", "--now", f"{UNIT}.timer"]])


def removal(platform: str = sys.platform) -> Job:
    home = Path.home()
    if platform == "darwin":
        plist = home / "Library" / "LaunchAgents" / f"{LABEL}.plist"
        uid = str(os.getuid()) if hasattr(os, "getuid") else "0"
        return Job({plist: ""}, [["launchctl", "bootout", f"gui/{uid}", str(plist)]])
    if platform == "win32":
        return Job({}, [["schtasks", "/Delete", "/F", "/TN", TASK]])
    units = home / ".config" / "systemd" / "user"
    return Job({units / f"{UNIT}.service": "", units / f"{UNIT}.timer": ""},
               [["systemctl", "--user", "disable", "--now", f"{UNIT}.timer"]])


Runner = Callable[[List[str]], int]


def _run(command: List[str]) -> int:
    try:
        return subprocess.run(command, capture_output=True, timeout=30).returncode
    except (OSError, subprocess.SubprocessError):
        return 1


def install(planned: Job, run: Optional[Runner] = None) -> List[str]:
    """Write the files, then activate. Returns what was done, for the report."""
    run = run or _run  # looked up at call time, so tests can replace it
    for path, text in planned.files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    done = [f"wrote {p}" for p in planned.files]
    for i, command in enumerate(planned.commands):
        code = run(command)
        optional = command[:2] == ["launchctl", "bootout"] and i == 0  # nothing to stop on the first install
        if code and not optional:
            raise OSError(f"'{' '.join(command[:3])}…' failed (exit {code})")
        done.append(" ".join(command[:3]))
    return done


def uninstall(planned: Job, run: Optional[Runner] = None) -> List[str]:
    """Deactivate, then remove the files that install wrote."""
    run = run or _run
    done = [" ".join(c[:3]) for c in planned.commands if run(c) == 0]
    for path in planned.files:
        if path.exists():
            path.unlink()
            done.append(f"removed {path}")
    return done
