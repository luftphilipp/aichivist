# aichivist – Concept

> An AI file clerk that works like an archivist: it reads every document, files it according to a plan you control,
> names it consistently, describes it in a catalog and logs every step so that nothing is lost and everything can be undone.

## Problem

Personal documents pile up in Downloads, cloud drives and phones: invoices, contracts, IDs, certificates, study material.

- **Rule-based tools** (e.g. Hazel, `organize`) sort by file name, type or date. They cannot tell that `scan_0042.pdf`
  is a health insurance policy or that `voucher.pdf` is a gift card.
- **AI organizers** (e.g. `llama-fs` and many small "AI file organizer" repos) read content, but rename and move files
  as a black box: no fixed filing plan, no catalog, no audit trail, no reliable undo.
- **Document management systems** (e.g. `paperless-ngx`) are powerful but need a server, a database and their own app.
  Files no longer live in normal folders or your own cloud.

## Idea

Use an AI coding agent (Claude Code) as an **archivist** that follows written rules, plus a small, well-tested helper
tool for every file operation. The human stays in charge of every decision that cannot be undone.

## Archival principles → implementation

| Principle (archival science) | What it means here |
|---|---|
| **Filing plan / classification scheme** (*Aktenplan*, ISO 15489) | A plain-language rules file defines fixed areas ("where does what go"). Files are filed by **subject**, not by document type. Anything outside the plan → ask the human. |
| **Provenance** (*Provenienzprinzip*) | Origin stays visible (e.g. "(Moodle)" in study material). Records of different people are never mixed (separate, untouchable areas per person). |
| **Original order & integrity** | Originals are never edited, converted or merged. SHA-256 checksums verify every copy between drives, detect duplicates and seal closed collections. |
| **Description / metadata** (*Erschliessung*) | One catalog per area: file, content summary, search terms, date. Search goes rules → catalog → original. |
| **Consistent naming** | `[YYYY-MM-DD ]Issuer DocumentType Subject[ No.][ v2].ext`, dates in ISO 8601 and **only if stated in the document**. |
| **Accountability / audit trail** | Every move and rename goes through one tool that writes a single log (time, old path, new path, action) and can undo any step. |
| **Appraisal & disposal** (*Bewertung / Kassation*) | Nothing is deleted directly. Duplicates and obsolete files go to a deletion list with a reason; only the human approves. Deletion = trash first. |
| **Open vs. closed collections** (*laufender vs. geschlossener Bestand*, records life cycle: active → inactive) | Every area has a status. **Open** areas still grow (current semester, ongoing applications): inboxes are watched, catalogs and full texts are provisional and updated on every run. **Closed** areas are complete (finished semesters, old jobs): catalog and full-text index are built once and marked final, the folder is marked closed, and the tool refuses to move files into or out of it unless the human explicitly re-opens it. Closing an area is a deliberate step with a final verification. |
| **Preservation & access** (OAIS idea, simplified) | Active records live where they are accessed (e.g. cloud for personal papers, local disk for code), media archives on external storage. |

## Workflow (one "tidy up" run)

1. **Collect**: every file in an inbox (Downloads, cloud inbox) is to be filed; in open collections, snapshots show
   what the human added or moved by hand since the last run (moves by hand → proposed rule change).
2. **Read** each file (text extraction, local OCR for scans) and decide **name and target** by the rules; unclear
   files stay and are collected as questions.
3. **Duplicates** (SHA-256) become `TRASH` rows instead of being filed.
4. **Filing plan**: one row per file (source, target, reason), simulated with `plan check`.
5. **Approval** by the human; only approved rows are applied. The plan records `done` / `error` per row.
6. **Catalog**: missing rows are added automatically and described by the agent.
7. **Verify**: catalog ↔ files complete; snapshots of the touched areas saved.
8. **Report** briefly: filed, open questions, deletion suggestions.

## Life cycle of an area

```
open (growing)  ──close──▶  closed (complete, read-only for the agent)
      ▲                            │
      └────────── reopen ──────────┘   (only with the human's approval, logged)
```

- **Open:** files arrive, get filed, the catalog and full-text index are updated each run and marked *provisional*.
- **Close:** final run → verify catalog ↔ files, build the final full-text index, write a closed marker (date, file count), log it.
- **Closed:** no moves in or out, no renaming; search works from the frozen catalog and index (no need to re-read files).
- **Reopen:** only on request (e.g. a late grade report), logged; then close again.

## Human in the loop

| Agent may do alone | Needs approval | Never |
|---|---|---|
| rename, move into folders the rules define, maintain catalogs | delete (trash), new folders, new storage locations, structural changes, **any change to the rules** | change original content, use external services (cloud OCR, uploads) without consent |

## Target users

People with many personal documents who use Claude Code (or a similar agent) and want lasting order **in their own
folders and cloud**, without handing their data to another system.

## Non-goals

No server, no own app, no database, no vendor lock-in. Everything stays in normal folders and plain-text files
(Markdown rules and catalogs, CSV log).

## Survey & storage advice (`aichivist survey`, `aichivist storage` – steps 1 and 4 done, 2–3 by the agent)

Before filing anything, archives take stock (*Bestandsaufnahme*). aichivist should do the same on first use and on request:

1. **Survey (tool, deterministic, local only):** scan the given locations (local folders, synced cloud folders,
   external drives) and report per location and area: number of files, total size, file types, folders with very many
   small files (code, datasets – bad for cloud sync), duplicates by checksum, files not opened for years, cloud files
   that exist only online.
   **Drive health:** for every drive involved, read the SMART status where possible – type (SSD/HDD), overall
   health, power-on hours, reallocated/pending sectors (HDD), wear level / spare (SSD), temperature – via
   `smartctl` (smartmontools; macOS, Linux, Windows) or OS tools (`diskutil`, PowerShell `Get-PhysicalDisk` /
   `Get-StorageReliabilityCounter`). Limits are reported honestly: many USB enclosures block SMART, admin rights may be
   needed, and "no data" never counts as "healthy". A worn or failing drive raises the risk in step 4 and the
   recommendation says so (e.g. "copy this drive first").
2. **Interview (agent):** ask what the scan cannot know – which cloud plan and price, which other storage media exist
   (external drives, NAS, second computer), what must be reachable from the phone, how important each area is.
3. **Recommendation (agent):** where each area should live, e.g.
   - personal papers → cloud (small, needed everywhere, off-site copy),
   - code and datasets → local + Git, never in the sync folder,
   - photo/video archives and closed collections → external drive or cloud, depending on price and risk,
   - duplicates and abandoned downloads → deletion list.
4. **Cost & risk comparison:** cloud subscription per year vs. one-time purchase of a local drive (spread over its
   lifetime), with the risk spelled out: a single drive is a single copy. The recommendation follows the
   **3-2-1 rule** (3 copies, 2 different media, 1 off-site) and shows what each option costs to reach it.
   Prices are **never hard-coded**: the user enters them or the agent looks up current prices and states the date.
   Done as `aichivist storage <storage.md>`: per area copies, kinds of storage, copies away from home and advice;
   cost per year per place (subscriptions per month/year, drives bought once spread over their lifetime).

The output is a short report (current state → recommendation → costs/risks → steps), and nothing is moved until the
human approves the steps.

## Deliverables (v0.1)

- `aichivist` CLI (stdlib only, Python 3.9+, Windows/macOS/Linux, `--json` for agents): `inventory`, `plan
  add/check/approve/apply`, `mv`, `trash`, `undo`, `note`, `duplicates`, `check-catalog`, `check-rules`, `close`,
  `reopen`, `status`, `verify`, `search`, `export-bag`, `validate-bag`, `protect`, `unprotect`, `protected`, `guard`
- **Filing plans** – the agent proposes, the human approves, the tool executes; the plan stays as the record
- **SHA-256 fixity**, closed collections with a full-text index (only when closed), **BagIt 1.0** export validated
  against the reference implementation bagit-python
- **Learning from corrections**: moves made by hand are flagged so the agent proposes a rule change
- **Claude Code plugin** (`plugin/`): skills `aichivist-setup` and `aichivist-filing`, guard hook for protected areas
- Rule templates (EN/DE), invented demo (`examples/`), CI with lint, type check and tests on three systems
