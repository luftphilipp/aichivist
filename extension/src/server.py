"""Entry point of the Claude Desktop extension: aichivist's MCP server with the folders chosen in the app."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # the bundled aichivist package lives next to this file

from aichivist import mcp_server  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--roots", nargs="*", default=[])
    parser.add_argument("--exclude", nargs="*", default=[])
    parser.add_argument("--rules", nargs="?", default="")
    args = parser.parse_args()
    roots = [r for r in args.roots if r]
    if not roots:
        print("aichivist: choose at least one folder in the extension settings", file=sys.stderr)
        return 1
    return mcp_server.serve(roots, args.rules or None, [e for e in args.exclude if e])


if __name__ == "__main__":
    sys.exit(main())
