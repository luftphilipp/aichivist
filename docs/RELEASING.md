# Releasing aichivist

Everything technical is prepared: tests run on Windows, macOS and Linux, the draft release **v0.1.0** has its notes
and the Claude Desktop extension attached, and `release.yml` publishes to PyPI when the release is published.
Three steps need the owner's accounts – they cannot be done by a script.

## 1. Make the repository public

GitHub → aichivist → **Settings** → **General** → bottom: **Change repository visibility** → Public.
Or in the terminal: `gh repo edit luftphilipp/aichivist --visibility public --accept-visibility-change-consequences`

Then **Settings → General → Social preview → Edit → Upload** `docs/social-preview.png`.

## 2. Allow GitHub to publish on PyPI (once)

1. Log in at <https://pypi.org> (create an account if needed, with two-factor authentication).
2. **Your account → Publishing → Add a new pending publisher** (GitHub tab):
   - PyPI project name: `aichivist`
   - Owner: `luftphilipp` · Repository: `aichivist`
   - Workflow name: `release.yml` · Environment name: `pypi`
3. On GitHub: **Settings → Environments → New environment** → `pypi` (no further settings needed).

No password or token is stored anywhere – PyPI trusts this workflow only.

## 3. Publish the release

GitHub → **Releases** → draft **aichivist 0.1.0** → **Edit** → **Publish release**.
Publishing creates the tag `v0.1.0`; `release.yml` then uploads the package to PyPI and attaches a freshly built
`aichivist-0.1.0.mcpb`. After a few minutes `pipx install aichivist` works for everyone.

## Later releases

1. Raise the version in `aichivist/__init__.py`, `pyproject.toml`, `extension/manifest.json`,
   `plugin/.claude-plugin/plugin.json` (also the pinned `aichivist[mcp]==…` in its `mcpServers`) and
   `gemini-extension.json` – the tests refuse mismatching versions.
2. Move the "unreleased" changelog entries under the new version.
3. Publish a release with the tag `vX.Y.Z`. `release.yml` then uploads to PyPI, attaches `aichivist-X.Y.Z.mcpb` and
   `aichivist.mcpb` (the README's download button), and updates the MCP Registry entry (`server.json`) by itself.
   Glama rebuilds automatically (auto-release); Anthropic's directory follows the `main` branch.
