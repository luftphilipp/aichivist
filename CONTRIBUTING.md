# Contributing

Thanks for helping! aichivist handles people's personal documents, so **safety beats features**.

## Ground rules
- Every file operation goes through `fileops` (never overwrite, log, verifiable, undoable).
- Closed collections stay read-only; new behaviour must respect `markers.closed_root`.
- No network access in the tool. Optional extras (pypdf, OCR) must degrade gracefully and say what is missing.
- Standard library only for the core; Python 3.9+; Windows, macOS and Linux.

## Workflow
1. Open an issue first for larger changes.
2. Write the test first (`tests/`, unittest, one sandbox per test via `SandboxTest`).
3. Run locally:
   ```bash
   python -m unittest discover -s tests
   ruff check aichivist tests examples
   mypy aichivist
   ```
4. Update `CHANGELOG.md` and, if behaviour changes, the templates and skills.
5. Never commit real documents or personal paths – use invented examples ("Example Health", "Alex Sample").

## Releasing

See [docs/RELEASING.md](docs/RELEASING.md).
