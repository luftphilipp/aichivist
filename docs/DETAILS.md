# aichivist – details

Everything technical in one place. Start with the [README](../README.md) for the short version.

## Manual MCP setup

For Cursor and other MCP apps (or Claude Desktop without the extension: *Settings → Developer → Edit Config*):

```json
{
  "mcpServers": {
    "aichivist": {
      "command": "aichivist",
      "args": ["mcp", "--root", "~/Downloads", "--root", "~/Documents", "--rules", "~/Documents/RULES.md"]
    }
  }
}
```

If Claude Desktop cannot find `aichivist`, put the full path from `which aichivist` (Windows: `where aichivist`)
under `"command"`. The AI can only see the folders you list with `--root`. It reads documents, proposes a plan, shows it to you – and
moves files only after you say yes.


Add `"--exclude", "~/Documents/Health"` for folders the AI must never see.

## What makes it different

- **Plan first, then act.** Every move is a row in a filing plan you approve; the plan stays as the record.
- **Nothing is lost.** Never overwrites, never deletes directly (trash only), byte-verified copies, one journal, `undo`.
- **Archival principles, not guesswork.** A filing plan you write, provenance, consistent names, catalogs.
- **Finished means finished.** Closed collections are sealed with SHA-256 checksums, become read-only and full-text
  searchable, and export as **BagIt** packages (Library of Congress standard) for long-term storage.
- **Rules that are enforced.** In Claude Code a guard hook blocks raw `mv`/`rm` in your filing areas.
- **Programs keep working.** Program folders, photo libraries, game and code folders, targets of links and open
  files are never moved by accident; if you want them moved, a link stays behind.

| | rule tools (Hazel, `organize`) | AI organizers (`llama-fs`, …) | DMS (`paperless-ngx`) | **aichivist** |
|---|---|---|---|---|
| understands content | – | ✓ | ✓ | ✓ |
| files by a plan you write | ✓ | – | partly | ✓ |
| preview & approval before anything moves | ✓ (simulate) | ✓ (UI) | – | ✓ (filing plan) |
| catalog, audit trail, undo | – | – | partly | ✓ |
| closed collections with fixity, BagIt export | – | – | – | ✓ |
| leaves program data alone (apps, libraries, links) | – | – | – | ✓ |
| backup check (3-2-1) and storage cost | – | – | – | ✓ |
| normal folders, own cloud, no server | ✓ | ✓ | – | ✓ |

## Archival principles inside

| Principle | In aichivist |
|---|---|
| Filing plan (*Aktenplan*, ISO 15489) | rules file: fixed areas, filing by subject, anything unknown → ask |
| Provenance | other people's records are never mixed or touched; source markers stay |
| Integrity / fixity | originals are never edited; SHA-256 verifies copies, finds duplicates, seals closed collections |
| Description (*Erschliessung*) | one catalog per area: content, search terms, date; gaps are found automatically |
| Open vs. closed collections | growing areas are updated each run; complete ones are **closed**: read-only, verifiable, searchable |
| Accountability | one journal for every step; filing plans record what was approved and done |
| Appraisal & disposal | nothing is deleted directly – duplicates go on the plan as `TRASH`, the human approves |
| Packaging for preservation | closed collections export as **BagIt** bags (RFC 8493) |

Concept: [CONCEPT.md](CONCEPT.md) · Walkthrough: [examples/](../examples/)

## Commands

| Command | What it does |
|---|---|
| `survey <places…>` | take stock: sizes, types, duplicates, unclear names, stale files, cloud-only files, drive health |
| `inventory <folder> [--save]` | files in an inbox; for areas what changed or was moved *by hand* since the last run |
| `plan add\|check\|approve\|apply <plan.md>` | filing plans: agent proposes, human approves, tool executes and records |
| `mv <source> <target>` / `trash <path>…` | safe move (never overwrites, verified across drives) / trash, both undoable |
| `photos <inbox> --to <photos> [--plan P]` | photos/videos into `<year>/[<subject>/]` by capture date, else file name date, else modified date; names kept |
| `catalog-page <area> [--open]` | all catalogs of an area as one searchable web page, files linked |
| `watch <inbox>… --install [--at 09:00]` / `--uninstall` | set up or remove the daily reminder (launchd, systemd, Task Scheduler) |
| `update [--check]` | install the newest version from GitHub whose tests passed (red tests keep the installed one) |
| `storage <storage.md> [--currency CHF]` | 3-2-1 check per area (copies, kinds of storage, away from home) and yearly cost of each storage place – prices from your table, never built in |
| `apps <path>…` | does a program depend on it? program folders, libraries (Photos, Lightroom, Obsidian, Steam …), code projects, links and shortcuts, open files |
| `mv … --leave-link` · plan mark `link` | move program data and leave a link at the old place so the program keeps working (`--app-data`: move anyway after adjusting the program) |
| `undo --last N` / `--since TIME` | revert file steps in reverse order; never touches closed collections |
| `duplicates <files or inbox> --in <area>` | identical files; keeps the cleanest name |
| `check-catalog <catalog.md> [--add-missing [--prefill]]` · `check-rules <rules.md>` | catalog ↔ files (`--prefill` writes a description read from the document, marked ◇) · unfilled placeholders, missing folders |
| `suggest <file>` | read a document: date, issuer, kind, keywords and a suggested file name |
| `style <area>` | naming examples (past renames, names per folder) so new names match |
| `similar <files or inbox> [--in <area>]` | the same document in a different file (new scan, re-download) – by text |
| `due <area> --years N [--plan P --archive DIR]` | retention period over → proposals: long-term archive, or TRASH to delete |
| `structure <folder> [--plan P]` | structure problems in plain language; simple fixes as plan proposals |
| `watch <inbox>… [--threshold 25]` | daily reminder only when enough files wait (exit code 3, system notification) |
| `plan review <plan.md>` | review and approve a plan on a local web page with checkboxes |
| `close` / `reopen` / `status` / `verify <folder>` | seal a complete collection, reopen it, check it |
| `search <closed folder> <terms>` | full-text search with page numbers |
| `export-bag <closed folder> <target>` / `validate-bag <bag>` | BagIt 1.0 package for long-term storage |
| `protect` / `unprotect <folder>`, `protected` | areas where the Claude Code guard hook blocks raw changes |
| `mcp --root <folder>… [--rules <file>]` | MCP server for Claude Desktop, Cursor and other MCP apps |

Messages follow the system language (English or German; `AICHIVIST_LANG=en|de` to choose). Add `--json` before
any command for machine-readable output. Optional extras: `aichivist[pdf]` (PDF text),
`aichivist[mcp]` (MCP server, Python 3.10+); `smartmontools` for drive health. Scans are read with the **built-in OCR**
of macOS (Vision) and Windows (Windows.Media.Ocr) – no installs; elsewhere [`ocrmypdf`](https://github.com/ocrmypdf/OCRmyPDF)
or [`tesseract`](https://github.com/tesseract-ocr/tesseract) are used if present.

## Safety & privacy

- The agent proposes; **you approve** every plan, deletion, new folder, change in a closed collection and any rule
  change. The tool never overwrites, never deletes directly, verifies copies and logs every step.
- **Program data is left alone**: moves and deletions of files a program depends on (program folders, libraries,
  code projects, targets of links/shortcuts, open files) are refused until you choose `--leave-link` or `--app-data`.
  iCloud Drive and other cloud folders count as your own files, even though they sit inside `~/Library`.
- The MCP server only reaches the folders given with `--root` (`..` and symlinks cannot escape); folders given with
  `--exclude` (e.g. health records) are invisible to the agent – not even their file names are shown.
- The Claude Code guard hook blocks moves, deletes, copies into and overwrites of protected areas. It is a safety net,
  not a sandbox – see [SECURITY.md](../SECURITY.md).
- The `aichivist` tool works **only locally**. The **AI** that reads your documents sends what it reads to its model
  provider – check its data policy, or use an MCP app with a local model.

## Roadmap

- Storage advice on top of `survey`: interview about storage media and cloud plan, cloud vs. local cost and risk
  (3-2-1 rule). See [docs/CONCEPT.md](CONCEPT.md).
- More agent integrations and more translations of the rule templates.

