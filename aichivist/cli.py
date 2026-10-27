"""Command line interface: the only way an agent should touch files (`aichivist [--json] <command> ...`)."""
import argparse
import json
import sys
from typing import List, Optional

from . import __version__, guard
from .commands import HANDLERS
from .fileops import FilingError
from .i18n import t


def _folder_cmd(sub, name, text, *extra):
    s = sub.add_parser(name, help=text)
    s.add_argument("folder")
    for flag in extra:
        s.add_argument(flag, default="")
    return s


def _overview(sub) -> None:
    """Take stock, without changing anything."""
    sub.add_parser("start", help="simple menu for first steps (what the Start files open)")

    s = sub.add_parser("survey", help="take stock: sizes, types, duplicates, unclear names, drive health (read only)")
    s.add_argument("places", nargs="+")
    s.add_argument("--stale-years", type=int, default=3, help="report files unchanged for this many years")
    s.add_argument("--no-duplicates", action="store_true", help="skip the duplicate search (faster)")

    s = sub.add_parser("inventory", help="new / changed / moved / removed files since the last snapshot")
    s.add_argument("folder")
    s.add_argument("--save", action="store_true", help="store the current state as the new snapshot")

    s = sub.add_parser("storage", help="3-2-1 check and yearly cost of your storage places (read only)")
    s.add_argument("table", help="Markdown table of storage places (run once to see the format)")
    s.add_argument("--currency", default="", help="shown after amounts, e.g. CHF")
    s.add_argument("--lifetime", type=float, default=5, help="years a drive bought once is used")

    s = sub.add_parser("apps", help="does a program depend on these paths? (read only)")
    s.add_argument("paths", nargs="+")

    s = sub.add_parser("structure", help="spot structure problems (too deep, empty, by file type …), propose fixes")
    s.add_argument("folder")
    s.add_argument("--plan", help="add the simple fixes as proposals to this filing plan")

    s = sub.add_parser("watch", help="remind only when enough files wait in an inbox (for daily schedules)")
    s.add_argument("inboxes", nargs="*")
    s.add_argument("--threshold", type=int, default=25)
    s.add_argument("--install", action="store_true", help="run this check every day (launchd / systemd / schtasks)")
    s.add_argument("--at", default="09:00", help="time of the daily check, HH:MM")
    s.add_argument("--uninstall", action="store_true", help="remove the daily check")


def _files(sub) -> None:
    """Moving, trash, undo, duplicates, photos."""
    s = sub.add_parser("mv", help="move or rename (never overwrites, logged)")
    s.add_argument("source")
    s.add_argument("target")
    s.add_argument("--create-folder", action="store_true", help="create a missing target folder (needs approval)")
    s.add_argument("--allow-closed", action="store_true", help="act inside a closed collection (needs approval)")
    s.add_argument("--leave-link", action="store_true", help="leave a link at the old place so programs keep working")
    s.add_argument("--app-data", action="store_true", help="move program data anyway (after adjusting the program)")

    s = sub.add_parser("trash", help="move to the trash (only after approval, logged, undoable)")
    s.add_argument("paths", nargs="+")
    s.add_argument("--allow-closed", action="store_true")
    s.add_argument("--app-data", action="store_true", help="delete program data anyway")

    s = sub.add_parser("photos", help="photos/videos into <photos>/<year>/[<subject>/] by capture date")
    s.add_argument("inbox")
    s.add_argument("--to", required=True, help="the photos root, e.g. a drive's Photos folder")
    s.add_argument("--plan", help="add the proposals to this filing plan")

    s = sub.add_parser("undo", help="revert logged steps in reverse order")
    scope = s.add_mutually_exclusive_group(required=True)
    scope.add_argument("--last", type=int, metavar="N", help="revert the last N steps")
    scope.add_argument("--since", metavar="TIME", help="revert every step at or after TIME (ISO 8601)")

    s = sub.add_parser("note", help="log a change made outside aichivist",
                       epilog="example: aichivist note move ~/Downloads/a.pdf ~/Archive/a.pdf")
    s.add_argument("action", help="what happened: move, rename or trash (undoable), or own words")
    s.add_argument("old", help="the path before")
    s.add_argument("new", help="the path after (or \"\" when there is none)")

    s = sub.add_parser("duplicates", help="identical files: new items vs. target area and among themselves")
    s.add_argument("paths", nargs="+", help="new files or inbox folders")
    s.add_argument("--in", dest="area", required=True, help="target area to compare with")

    s = sub.add_parser("similar", help="near-duplicates: the same document in different files (by text)")
    s.add_argument("paths", nargs="+")
    s.add_argument("--in", dest="area", help="compare with this area instead of among the paths")
    s.add_argument("--threshold", type=float, default=0.8)


def _plans(sub) -> None:
    """Filing plans: the agent proposes, the person approves."""
    s = sub.add_parser("plan", help="filing plans: propose, approve, check, apply")
    plans = s.add_subparsers(dest="plan_command", required=True)
    s = plans.add_parser("add", help="propose one row (agent)")
    s.add_argument("plan")
    s.add_argument("source")
    s.add_argument("target", help="target path, or TRASH")
    s.add_argument("--reason", required=True)
    s = plans.add_parser("approve", help="approve proposed rows (human)")
    s.add_argument("plan")
    s.add_argument("--rows", type=lambda v: [int(x) for x in v.split(",")], help="e.g. 1,3,4 (default: all)")
    s.add_argument("--link", action="store_true", help="leave a link at the old place (program data)")
    for name, text in (("check", "simulate without touching files"),
                       ("apply", "execute approved rows and record the result in the plan")):
        s = plans.add_parser(name, help=text)
        s.add_argument("plan")
        s.add_argument("--create-folders", action="store_true", help="create missing target folders (approved)")
    plans.add_parser("review", help="review and approve the plan on a local web page").add_argument("plan")


def _catalogs(sub) -> None:
    """Catalogs, names, rules, retention."""
    s = sub.add_parser("catalog-page", help="all catalogs of an area as one searchable web page")
    s.add_argument("area")
    s.add_argument("--out", help="where to write the page (default: aichivist's own folder)")
    s.add_argument("--open", action="store_true", help="open it in the browser")

    s = sub.add_parser("check-catalog", help="every file in the catalog and every entry on disk?")
    s.add_argument("catalog")
    s.add_argument("--add-missing", action="store_true", help="append rows for uncatalogued files to describe")
    s.add_argument("--prefill", action="store_true", help="with --add-missing: prefill rows from the document text (◇)")

    sub.add_parser("suggest", help="read a document and suggest date, issuer, kind, keywords and a name").add_argument(
        "file")
    sub.add_parser("style", help="naming examples of an area (past renames, names per folder)").add_argument("area")

    s = sub.add_parser("due", help="records whose retention period is over – propose archive or deletion")
    s.add_argument("area")
    s.add_argument("--years", type=float, required=True)
    s.add_argument("--plan", help="add one proposal row per record to this filing plan")
    s.add_argument("--archive", help="long-term archive folder (otherwise the proposal is TRASH)")

    s = sub.add_parser("check-rules", help="unfilled placeholders and missing folders in a rules file")
    s.add_argument("rules")


def _collections(sub) -> None:
    """Closed collections and BagIt."""
    _folder_cmd(sub, "close", "close a complete collection (fixity manifest + full-text index)", "--note")
    _folder_cmd(sub, "reopen", "reopen a closed collection (needs approval)", "--note")
    _folder_cmd(sub, "status", "open or closed?")
    _folder_cmd(sub, "verify", "check a closed collection against its manifest")

    s = sub.add_parser("search", help="search the full-text index of a closed collection")
    s.add_argument("folder")
    s.add_argument("query", nargs="+")

    s = sub.add_parser("export-bag", help="export a closed collection as a BagIt bag")
    s.add_argument("folder")
    s.add_argument("target")
    sub.add_parser("validate-bag", help="check a BagIt bag").add_argument("bag")


def _maintenance(sub) -> None:
    """Keeping aichivist itself up to date."""
    s = sub.add_parser("update", help="install the newest version from GitHub whose tests passed")
    s.add_argument("--check", action="store_true", help="only show the newest tested version")


def _agents(sub) -> None:
    """Guard hook and MCP server for AI agents."""
    _folder_cmd(sub, "protect", "block raw mv/rm by the agent in this folder (Claude Code hook)")
    _folder_cmd(sub, "unprotect", "remove a folder from the protected areas")
    sub.add_parser("protected", help="list protected areas")
    sub.add_parser("guard", help="Claude Code PreToolUse hook (reads the tool call as JSON from stdin)")

    s = sub.add_parser("mcp", help="MCP server for Claude Desktop and other MCP clients (needs aichivist[mcp])")
    s.add_argument("--root", dest="roots", action="append", required=True,
                   help="folder the agent may work in (repeat for several); nothing outside is reachable")
    s.add_argument("--rules", help="your filing rules file, served to the agent")
    s.add_argument("--exclude", action="append", default=[],
                   help="folder inside a root the agent must never see (repeat for several)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aichivist", description="Archival-grade file operations for AI filing agents.")
    p.add_argument("--version", action="version", version=f"aichivist {__version__}")
    p.add_argument("--json", action="store_true", help="machine-readable output for agents")
    sub = p.add_subparsers(dest="command", required=True)
    _overview(sub)
    _files(sub)
    _plans(sub)
    _catalogs(sub)
    _collections(sub)
    _agents(sub)
    _maintenance(sub)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    if args.command == "guard":
        return guard.main()
    if args.command == "start":
        from . import start
        return start.menu()
    if args.command == "mcp":
        try:
            from . import mcp_server
        except ImportError:
            print("the MCP server needs the extra: pip install \"aichivist[mcp]\" (Python 3.10+)", file=sys.stderr)
            return 1
        return mcp_server.serve(args.roots, args.rules, args.exclude)
    try:
        out = HANDLERS[args.command](args)
    except (FilingError, OSError) as err:
        kind = t("refused") if isinstance(err, FilingError) else t("error")  # rule vs. file system (disk full …)
        if args.json:
            print(json.dumps({"ok": False, "command": args.command, "error": f"{kind}: {err}"}, ensure_ascii=False))
        else:
            print(f"{kind}: {err}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"ok": out.code == 0, "command": args.command, "data": out.data},
                         ensure_ascii=False, default=str, indent=1))
    else:
        print("\n".join(out.lines))
    return out.code


if __name__ == "__main__":
    sys.exit(main())
