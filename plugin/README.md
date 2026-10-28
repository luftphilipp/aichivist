# aichivist – clean up your files like an archivist

aichivist lets Claude tidy up your documents the way a professional archivist would. Claude reads each document,
proposes a filing plan with clear names and the right folders, and moves nothing until you approve the plan. Duplicates
are found by content and go to the trash only after your OK. Game folders, photo libraries and code projects are
recognised and left alone, and every step is logged and can be undone.

## What it adds to Claude
- **MCP server `aichivist`** with tools to look at folders, read documents (first page first, to save tokens), suggest
  names for a whole folder in one call, find duplicates, build and check filing plans, keep catalogs and seal finished
  collections with checksums.
- **Skill `aichivist-setup`**: looks at your folders and proposes a complete setup you confirm with one answer.
- **Skill `aichivist-filing`**: the "tidy up" workflow – plan, your approval, filing, catalog.
- **Guard hook** (Claude Code): blocks raw `mv`/`rm` in folders you protected, so every change stays logged and
  undoable. It only runs when the aichivist command-line tool is installed.

## Install
In Claude Code: `/plugin install aichivist --marketplace luftphilipp/aichivist`, then say "Set up aichivist."

## Requirements and settings
The MCP server runs locally with `uvx` (from [uv](https://docs.astral.sh/uv/)); it installs the pinned aichivist
release from PyPI the first time. When you enable the plugin you choose the folder Claude may organize, optionally a
private folder Claude must never see, and optionally your filing rules file.

## Example prompts
1. "Tidy up my Downloads." – Claude suggests names and folders for every file and shows the plan before anything moves.
2. "Find duplicates in my Downloads that I already have in Documents." – identical files are proposed for the trash.
3. "Which of my folders are badly structured?" – plain-language advice, then a plan you approve.

## Privacy Policy
aichivist runs entirely on your computer: no account, no server, no telemetry, nothing is sent to the author. Claude
receives the content of the documents it reads through aichivist, under your AI provider's privacy terms; you choose
the shared folder and can exclude a private one. Full policy:
<https://github.com/luftphilipp/aichivist/blob/main/PRIVACY.md>

## Support
Issues and questions: <https://github.com/luftphilipp/aichivist/issues> · License: MIT
