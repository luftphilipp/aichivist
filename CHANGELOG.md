# Changelog

All notable changes are listed here. Format: [Keep a Changelog](https://keepachangelog.com/), versions: [SemVer](https://semver.org/).

## [Unreleased]

### Added
- Setup for other AI apps in the README: one-click installs for Cursor and VS Code / GitHub Copilot, Codex and
  Antigravity CLI configuration, and `gemini-extension.json` for Gemini CLI.
- Releases update the MCP Registry entry automatically (GitHub OIDC, no stored secret).

## [0.1.1] – 2026-10-28

### Changed (fewer tokens)
- `read_document` returns the first page (2,500 characters) by default; `next_offset` reads on only when needed.
- New `suggest_names` (MCP) and `aichivist suggest <folder>` (CLI): date, issuer, kind and a name for every file of a
  folder in one call; the filing skill and the agent template start there.
- Tool definitions about a third smaller: shorter descriptions, no output schemas, and results are sent once instead
  of twice (no duplicate structured content). Folder listings stop at 100 entries and give the total.

### Added
- Claude plugin ready for Anthropic's directory: it brings the MCP server (`uvx`, pinned release), asks for the folder
  to organize, an optional private folder and the rules file; plugin README, icon and listing links.
- Privacy policy (`PRIVACY.md`), linked from the README, the plugin and the Claude Desktop extension.
- Download buttons in the README; every release also carries `aichivist.mcpb` without a version in its name.
- Every MCP tool has a title, and the server reports its version.

### Fixed
- Empty plugin or extension settings no longer reach the server as empty paths.
- The guard hook runs as a script inside the plugin (`hooks/guard.sh`).

## [0.1.0] – 2026-10-27

### Fixed (from a field report)
- Moving onto drives without file flags (exFAT) no longer stops with "Invalid argument": content and dates are kept,
  the byte-for-byte check stays.
- Links that lead nowhere can be moved, trashed and restored; between drives a link moves as a link.
- Trash on another drive uses that drive's own trash (`.Trashes/<uid>`, `.Trash-<uid>`) instead of copying to the
  home drive.
- Program check: a project next to the target no longer blocks filing into that folder; unreadable folders no longer
  stop the check; hidden folders below `~/Documents` (own rule folders) are not program folders, and the message names
  the right folder; refusing `trash` names `--app-data` as the way to delete anyway.
- Plans: `|` in names and spaces at the start or end of names survive the plan file; `plan check` knows folders that
  an earlier row creates; `plan apply` lists each failed row with its reason.
- `check-catalog --add-missing` writes the rows to describe in the catalog's language (German or English).
- `note --help` names the actions and gives an example.

### Changed (first steps)
- Setup in Claude Code looks at the folders first and proposes the whole setup for one confirmation instead of an
  interview; it installs the command-line tool itself (after asking) and offers the first tidy-up right away. Codex,
  Gemini CLI and Cursor get the same short setup in `templates/AGENTS.md`.
- The start menu shows only the way for the AI app installed on the computer (or recommends Claude Desktop with its
  download link) and points to it after looking at a folder.
- `Start (Mac).command` recognises a new Mac without Python and lets macOS install it.
- The plugin's guard hook stays silent until the command-line tool is installed.
- README: one main way to start; the others folded; current steps for the macOS and Windows warning on first start.

### Added
- `survey`: take stock of places without AI – sizes, types, duplicates, unclear names, stale files, cloud-only files
  (never downloaded), folders unsuitable for cloud sync, free space and drive health (smartctl / diskutil).
- MCP server (`aichivist mcp --root …`, extra `aichivist[mcp]`) for Claude Desktop, Cursor and other MCP apps: reading
  documents, filing plans, catalogs and search, restricted to the shared folders; works with MCP SDK 1.x and 2.x.
- Name suggestions and prefilled catalog rows read from the document (`suggest`, `check-catalog --prefill`): date
  (skipping birth dates), issuer (legal form or web domain), kind in the document's language, subject.
- `structure`: plain-language structure advice (too deep, empty or one-file folders, folders by file type,
  duplicate folder names, too many top-level folders); simple fixes as plan proposals.
- Naming style examples (`style`), near-duplicates by text (`similar`), retention periods with the choice long-term
  archive or deletion (`due`), reminder from a threshold (`watch`), plan review page with checkboxes (`plan review`);
  all also as MCP tools.
- Built-in OCR without installs: macOS Vision (JavaScript for Automation) and Windows.Media.Ocr (PowerShell), used
  before ocrmypdf/tesseract for scanned PDFs and images.
- Claude Desktop extension (`aichivist-<version>.mcpb`, built by `extension/build.py`): install by double-click, choose
  folders, excluded folders and rules file in the app; Python and dependencies are installed by the app (uv).
- MCP `--exclude <folder>`: zones inside a shared folder that the agent can neither read nor list nor see in surveys.
- `catalog.describe` / MCP `catalog_describe`: fill one "⚠ to describe" row.
- `storage`: 3-2-1 check per area (three copies, two kinds of storage, one away from home) and yearly storage cost,
  from a Markdown table of the person's storage places; prices are never built in. Also as MCP tool `storage_check`.
- Rule templates in French (`REGLES.md`), Italian (`REGOLE.md`) and Spanish (`REGLAS.md`); catalogs may be named
  `_catalogue.md` / `_catalogo.md`. `templates/AGENTS.md` for Codex, Gemini CLI, Cursor and other agents.
- `update`: installs the newest version from GitHub – only one whose tests passed there; a red or running test
  run keeps the installed version. Personal rules, catalogs and journals are never touched.
- Double-click start for downloaded copies: `Start (Mac).command`, `Start (Windows).bat`, `start.sh` open
  `aichivist start`, a numbered menu (look at Downloads or another folder, backup check, catalog page, reminder,
  connect an AI, install) – no installation needed.
- Messages in German on German systems (Swiss spelling with "ss" on de_CH); `AICHIVIST_LANG=en|de` overrides.
- `photos <inbox> --to <photos> [--plan P]`: photos and videos into `<year>/[<subject>/]` by capture date (EXIF, video
  header, Spotlight for HEIC), else a date in the file name, else the modified date; names are kept. Plans can create
  the approved new folders with `plan apply --create-folders`. Also as MCP tool `plan_photos`.
- `watch <inbox> --install [--at 09:00]` / `--uninstall`: the daily reminder via launchd, a systemd user timer or the
  Windows Task Scheduler; notifications now also on Windows.
- `catalog-page <area> [--open]`: all catalogs of an area as one searchable web page (stays on the computer).
  Catalogs may list files relative to a heading that names a sub-folder ("## Insurance").
- Catalog checks treat umlauts the same however they are stored (macOS keeps "ü" in file names as "u" + dots).
- Windows: `--leave-link` without Developer Mode – a junction for folders, a hard link for files.
- `survey` lists program folders (games, photo libraries, apps) to leave alone. Name suggestions take the subject
  from the words after the document kind ("Policy basic insurance") and never use half a sentence as issuer.
- README: feature overview (`docs/features.svg`), before/after with a game folder that stays, demo with `suggest`,
  `apps` and `storage`.
- Program data is protected: moving or deleting files a program depends on (program folders such as Library/AppData,
  libraries such as Photos, Lightroom, Obsidian, Steam, code projects, targets of links or Windows shortcuts, files
  open in a program) is refused; `apps <path>` explains why. `--leave-link` / plan mark `link` moves it and leaves a
  link at the old place so the program keeps working (undo removes the link); `--app-data` moves anyway.
- Linux: files moved to the trash get a freedesktop `.trashinfo`, so the file manager can restore them (undo removes
  it again).
- Reproducible README demo (`examples/make_demo_svg.py` → `docs/demo.svg`).
- Safe file operations: `mv` (never overwrites, byte-verified across drives), `trash`, `undo --last/--since`, `note`.
- Single journal for every operation; `undo` skips steps that would touch a closed collection.
- `inventory`: new / changed / moved / removed since the last snapshot; moves not made through aichivist are flagged
  as *by hand* (corrections the rules may need to learn).
- Open vs. closed collections: `close` (SHA-256 fixity manifest + full-text index), `reopen`, `status`, `verify`.
- Full-text index **only for closed collections**: text, docx, pptx, xlsx built in; PDF via optional `pypdf`;
  scans via optional `ocrmypdf`; images via optional `tesseract`; `search`.
- BagIt 1.0 export and validation (`export-bag`, `validate-bag`), validated against the reference bagit-python.
- Filing plans: `plan add / check / approve / apply` – the agent proposes, the human approves, the plan records results.
- `duplicates` (size → head/tail sample → SHA-256; keeps the name without "copy", "(1)" …).
- `check-catalog [--add-missing]`, `check-rules`.
- Protected areas (`protect`, `unprotect`, `protected`) and the Claude Code guard hook (`guard`, Bash and PowerShell):
  blocks moves, deletes, copies into protected areas and overwriting redirects.
- Closed collections cannot be moved, trashed or nested inside another closed collection; `undo` counts only file
  steps and never reverts a step twice; BagIt export refuses collections that changed since closing.
- Claude Code plugin with the skills `aichivist-setup` and `aichivist-filing`; rule templates in English and German.
- `--json` output for agents; Windows, macOS and Linux.
