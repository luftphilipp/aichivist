"""`aichivist update` – install the newest version from GitHub, but only one whose tests passed there.

GitHub is the source: whatever was pushed to `main` and passed the tests on Windows, macOS and Linux is installed for
the current user. A red or still running test run keeps the installed version, so a broken change never reaches the
filing rules. The Claude Desktop extension is a separate copy: it is updated by double-clicking a new .mcpb.
"""
import json
import shutil
import ssl
import subprocess
import sys
import urllib.request
from typing import NamedTuple, Optional

from . import __version__

REPO = "luftphilipp/aichivist"
RUNS = f"https://api.github.com/repos/{REPO}/actions/workflows/tests.yml/runs?branch=main&per_page=1"
TIMEOUT = 30


class Latest(NamedTuple):
    commit: str
    passed: bool
    state: str    # "success", "failure", "in_progress" …


def _token() -> Optional[str]:
    """A GitHub token from the gh command line tool, needed while the repository is private."""
    gh = shutil.which("gh")
    if not gh:
        return None
    try:
        out = subprocess.run([gh, "auth", "token"], capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def _tls() -> ssl.SSLContext:
    """python.org builds on macOS ship without certificates: use certifi when it is there."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def latest() -> Latest:
    """The newest test run on main: which commit, and did it pass?"""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"aichivist/{__version__}"}
    token = _token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(RUNS, headers=headers)
    with urllib.request.urlopen(request, timeout=TIMEOUT, context=_tls()) as response:
        runs = json.load(response)["workflow_runs"]
    if not runs:
        return Latest("", False, "no test run")
    run = runs[0]
    state = run["conclusion"] or run["status"]
    return Latest(run["head_sha"], run["conclusion"] == "success", state)


def install(commit: str) -> int:
    source = f"git+https://github.com/{REPO}@{commit}"
    # --force-reinstall: between releases the version number stays the same, but the code is newer
    command = [sys.executable, "-m", "pip", "install", "--user", "--force-reinstall", "--no-deps", "--quiet", source]
    return subprocess.run(command, check=False).returncode
