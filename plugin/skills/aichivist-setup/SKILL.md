---
name: aichivist-setup
description: Set up aichivist for a new person – look at their folders, propose filing rules they only need to confirm, create catalogs and install the trigger so every later filing task follows the rules. Use when the user says "set up aichivist", "richte aichivist ein" or wants to start organizing their documents with aichivist.
---

# aichivist setup

Goal: after this setup, "tidy up" (or "räum auf") files everything according to rules the person understands and approved.
Nothing is moved, renamed or deleted during setup. Speak the person's language and keep messages short.
**Ask as little as possible:** look first, then propose a complete setup the person only confirms. Aim for one or two
answers in total; ask a further question only when the folders do not answer it.

## 1. Check the tool
Run `aichivist --version`. If it is missing, ask once: "May I install aichivist (a small, free program)?" Then use the
first that exists: `uv tool install aichivist`, `pipx install aichivist`, `python3 -m pip install --user aichivist`.
If the package is not found, install from GitHub instead (`… git+https://github.com/luftphilipp/aichivist`).

## 2. Look (read only, no questions)
Find the usual places yourself: Downloads, Desktop, Documents, synced cloud folders (macOS
`~/Library/Mobile Documents/com~apple~CloudDocs`, `~/Library/CloudStorage/*`; Windows OneDrive), mounted external
drives. Run `aichivist survey <places…>` once, and read only samples (a few file names, first pages) – never everything.
Do not save inventory baselines for inboxes (Downloads, Desktop): their files must stay "to be filed".

## 3. Propose – one confirmation
From what you saw, propose the whole setup at once, in at most 10 short lines:
- **Areas** found in the files (e.g. personal papers, applications, study/work, projects, photos) and where each lives:
  what is needed on the phone → cloud folder; large, code or program data → local.
- **Names:** `YYYY-MM-DD Issuer Kind Subject`, in the language of most file names.
- **Other people's records** (folders named after other persons, a partner's or client's files): own area, never
  touched.
- **Safety:** deleting only after the person's OK, always to the trash; every step undoable.
- **Catalogs:** one list per area, filled during the first tidy-up.

Then ask exactly one question: "Shall I set it up like this? (yes / tell me what to change)". Ask a second question
only for something the folders cannot tell (e.g. whether a folder of another person's name may be touched).

## 4. Write the rules
Copy `templates/RULES.md` (EN), `REGELN.md` (DE), `REGLES.md` (FR), `REGOLE.md` (IT) or `REGLAS.md` (ES) from the
aichivist repository to the place the agent reads (Claude Code: `~/Documents/CLAUDE.md` or a folder the person
chooses) and fill every `<placeholder>` from the confirmed proposal. Run `aichivist check-rules <rules file>` until it
reports no placeholders and no missing folders; folders that the proposal named were approved with it. Offer to show
the finished rules in full; change them later only with the person's approval.

## 5. Trigger and protection (part of the confirmed proposal)
Add this line to the user's global agent instructions (Claude Code: `~/.claude/CLAUDE.md`):

```
- Filing: before any task with documents, downloads or filing, read <path to rules> and follow it.
```

Without it the agent will not know the rules exist. Then `aichivist protect <folder>` for every filing area: with the
aichivist plugin installed, its guard hook blocks raw `mv`/`rm` there, so every change is logged and undoable.
Create an empty catalog (`_catalog.md`, header `| File | Content | Search terms | Date |`, or the German header
`| Datei | Inhalt | Suchbegriffe | Datum |`) in each area. Create `open-items.md` in the state folder.

## 6. Finish – and start right away
Report in three lines: rules (path), areas protected, catalogs created. Then offer the first run directly:
"Shall I tidy up your Downloads now? You will see the plan before anything moves."

Offer later, one at a time and not during setup: the backup check (`aichivist storage`, 3-2-1 and yearly cost),
closing finished collections (`aichivist close`, only after the person confirms), and a reminder when files pile up
(`aichivist watch <folder> --install`).
