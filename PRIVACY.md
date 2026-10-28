# Privacy Policy

*Effective 2026-10-28 · applies to aichivist (command-line tool, MCP server, Claude plugin and Claude Desktop extension)*

aichivist is open-source software that runs entirely on your own computer. There is no aichivist server, account,
analytics or telemetry.

## Data collection
aichivist collects no personal data and sends nothing to its author or to any service run for aichivist.

## Usage and storage
aichivist reads the files in the folders you share with it, in order to describe, name, file and catalog them. It
stores only on your computer:
- a journal of every file step it performed (for `undo`) and folder snapshots, in `~/.aichivist`
- filing plans, catalogs and checksum manifests, in the folders you work with

## Third-party sharing
aichivist itself shares nothing. Two things to know:
- **Your AI assistant** (for example Claude) receives the content of the documents it reads through aichivist. That
  data is handled under the privacy terms of your AI provider. You choose which folders are shared and can exclude
  folders completely, so private documents are never read.
- **Network access** happens only when you ask for it: `aichivist update` asks GitHub for the newest tested version,
  and installing aichivist (for example with `pip`, `pipx` or `uvx`) downloads it from PyPI.

## Data retention
Everything aichivist stores stays on your computer until you delete it. Delete `~/.aichivist` to remove the journal
and snapshots; plans and catalogs are ordinary files in your folders.

## Contact
Questions or concerns: open an issue at <https://github.com/luftphilipp/aichivist/issues>, or report a security
problem privately as described in [SECURITY.md](SECURITY.md).
