"""`aichivist start` – a simple numbered menu for people who just downloaded aichivist and never used a terminal.

Started by double-clicking `Start (Mac).command`, `Start (Windows).bat` or `start.sh` in the downloaded folder; no
installation needed (aichivist only uses Python's standard library). Everything in the menu only reads, except
setting up the reminder and installing, which ask first.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, Tuple

from . import catalog_page, schedule, storage, survey
from .config import full_path
from .i18n import t

Ask = Callable[[str], str]
Say = Callable[[str], None]
ROOT = Path(__file__).resolve().parent.parent
AI_LINKS = "https://github.com/luftphilipp/aichivist#get-started"
# one way per AI app – the menu shows only the ways for apps installed on this computer
AI_STEPS: Dict[str, str] = {
    "Claude Desktop": "Claude Desktop: download aichivist-<version>.mcpb from the releases page, double-click it, "
                      "choose the folders Claude may organize, then ask: \"Tidy up my Downloads.\"",
    "Claude Code": "Claude Code: type /plugin marketplace add luftphilipp/aichivist, then /plugin install "
                   "aichivist@aichivist, then say: \"Set up aichivist.\"",
    "Codex": "Codex, Gemini CLI, Cursor: copy templates/AGENTS.md from this folder to where your AI reads its "
             "instructions.",
}
COMMANDS = {"Claude Code": "claude", "Codex": "codex"}
DESKTOP_PLACES = [Path("/Applications/Claude.app"), Path.home() / "Applications" / "Claude.app",
                  Path(os.environ.get("LOCALAPPDATA", "~")).expanduser() / "AnthropicClaude"]
CLAUDE_DOWNLOAD = "https://claude.ai/download"
YES = ("y", "yes", "j", "ja")
REMINDER_THRESHOLD = 25
REMINDER_TIME = "09:00"


def _folder(ask: Ask, say: Say, default: str = "") -> Path:
    hint = f" [{default}]" if default else ""
    answer = ask(t("Folder (drag it into this window, or type the path){hint}: ", hint=hint)).strip().strip("'\"")
    folder = full_path(answer or default)
    if not folder.is_dir():
        raise ValueError(t("Not a folder: {folder}", folder=folder))
    return folder


def _survey(folder: Path, say: Say) -> None:
    say(t("Looking at {folder} – nothing is changed …", folder=folder))
    for line in survey.render(survey.run([folder], progress=False)):
        say(line)
    say(t("Next: choose 6 – it shows the quickest way to let an AI tidy up on this computer."))


def _storage(ask: Ask, say: Say) -> None:
    answer = ask(t("Your storage table (Markdown file; leave empty to see the format): ")).strip().strip("'\"")
    table = full_path(answer or "storage.md")
    if not table.is_file():
        say(t("List your storage places in a file like this, then choose this option again:"))
        say(storage.EXAMPLE)
        return
    for line in storage.render(storage.check(table)):
        say(line)


def _install(ask: Ask, say: Say) -> None:
    if ask(t("Install aichivist for your user so it works from everywhere? [y/N] ")).strip().lower() not in YES:
        return
    done = subprocess.run([sys.executable, "-m", "pip", "install", "--user", str(ROOT)], check=False)
    say(t("Installed. From now on: python3 -m aichivist <command>") if done.returncode == 0
        else t("Installation failed – aichivist still works from this folder."))


def _reminder(ask: Ask, say: Say) -> None:
    folder = _folder(ask, say, str(Path.home() / "Downloads"))
    question = t("Remind you every morning once {n} files wait in {folder}? [y/N] ", n=REMINDER_THRESHOLD,
                 folder=folder)
    if ask(question).strip().lower() in YES:
        for line in schedule.install(schedule.job([folder], REMINDER_THRESHOLD, REMINDER_TIME)):
            say(line)


def installed_ai() -> List[str]:
    """AI apps found on this computer, in the order of AI_STEPS."""
    found = {name for name, command in COMMANDS.items() if shutil.which(command)}
    if any(place.exists() for place in DESKTOP_PLACES):
        found.add("Claude Desktop")
    return [name for name in AI_STEPS if name in found]


def _ai_steps(say: Say) -> None:
    apps = installed_ai()
    if not apps:
        say(t("No AI app found on this computer. The easiest one: Claude Desktop – {link}", link=CLAUDE_DOWNLOAD))
        apps = ["Claude Desktop"]
    for number, name in enumerate(apps, 1):
        say(f"  {number}. {t(AI_STEPS[name])}")
    say("  " + t("The AI proposes a plan; nothing is moved before you say yes."))
    say(t("Instructions: {link}", link=AI_LINKS))


def options(ask: Ask, say: Say) -> List[Tuple[str, Callable[[], None]]]:
    downloads = Path.home() / "Downloads"
    return [
        (t("Look at my Downloads (nothing is changed)"), lambda: _survey(downloads, say)),
        (t("Look at another folder"), lambda: _survey(_folder(ask, say), say)),
        (t("Are my backups safe? (3-2-1 check)"), lambda: _storage(ask, say)),
        (t("Searchable page of my catalogs"), lambda: say(str(catalog_page.write(_folder(ask, say), open_page=True)))),
        (t("Daily reminder when files pile up"), lambda: _reminder(ask, say)),
        (t("Let an AI tidy up (Claude Desktop, Claude Code, …)"), lambda: _ai_steps(say)),
        (t("Install aichivist permanently"), lambda: _install(ask, say)),
    ]


def menu(ask: Ask = input, say: Say = print) -> int:
    say(t("aichivist – your AI tidies up your documents like an archivist."))
    choices = options(ask, say)
    while True:
        say("")
        for number, (label, _) in enumerate(choices, 1):
            say(f"  {number}  {label}")
        say(f"  0  {t('Quit')}")
        try:
            choice = ask(t("Your choice: ")).strip()
            if choice in ("0", "", "q"):
                return 0
            if not choice.isdigit() or not 1 <= int(choice) <= len(choices):
                say(t("Please type a number from the list."))
                continue
            choices[int(choice) - 1][1]()
        except (ValueError, OSError) as err:
            say(t("That did not work: {error}", error=err))
        except (EOFError, KeyboardInterrupt):
            return 0
