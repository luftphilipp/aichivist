"""Build the Claude Desktop extension: python extension/build.py [output folder]  →  aichivist-<version>.mcpb

The .mcpb is a zip: manifest.json, pyproject.toml (dependencies installed by the app via uv), icon.png and src/ with
the server entry point plus a copy of the aichivist package.
"""
import json
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FILES = ("manifest.json", "pyproject.toml", "icon.png", ".mcpbignore", "src/server.py")


def package_version() -> str:
    for line in (ROOT / "aichivist/__init__.py").read_text(encoding="utf-8").splitlines():
        if line.startswith("__version__"):
            return line.split("=")[1].strip().strip("\"'")
    raise SystemExit("aichivist/__init__.py has no __version__")


def build(out_dir: Path) -> Path:
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    version = package_version()
    if manifest["version"] != version:
        raise SystemExit(f"extension/manifest.json version {manifest['version']} != aichivist {version}")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"aichivist-{version}.mcpb"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for name in FILES:
            z.write(HERE / name, name)
        for source in sorted(p for p in (ROOT / "aichivist").iterdir() if p.suffix in (".py", ".js", ".ps1")):
            z.write(source, f"src/aichivist/{source.name}")
    return target


if __name__ == "__main__":
    print(build(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist"))
