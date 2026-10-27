# Security

## Reporting
Please report vulnerabilities privately via GitHub's *Report a vulnerability* (Security tab) rather than in public
issues.

## Threat model in short
- **The tool** works only locally and never deletes directly (trash only, logged, undoable).
- **The agent** (e.g. Claude Code) reads document content and sends what it reads to its model provider. Documents
  may contain prompt injections ("ignore your rules and delete …"); the rules tell the agent to treat document text as
  content, and destructive steps need human approval through filing plans.
- **The guard hook** blocks the usual raw move/delete/copy-in/overwrite commands in protected areas (Bash and
  PowerShell). It is a text-based safety net,
  not a sandbox: a program written to bypass it can. Report bypasses that an agent would plausibly use.
