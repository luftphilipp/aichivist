import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import aichivist

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("mcpb_build", ROOT / "extension" / "build.py")
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)


class ExtensionBuildTest(unittest.TestCase):
    def test_bundle_contains_manifest_server_and_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = build.build(Path(tmp))
            names = set(zipfile.ZipFile(bundle).namelist())
            manifest = json.loads(zipfile.ZipFile(bundle).read("manifest.json"))

        self.assertTrue({"manifest.json", "pyproject.toml", "icon.png", "src/server.py",
                         "src/aichivist/mcp_server.py", "src/aichivist/agent_tools.py"} <= names)
        self.assertEqual(manifest["version"], aichivist.__version__)
        self.assertEqual(manifest["server"]["type"], "uv")

    def test_manifest_points_to_existing_entry_point_and_icon(self):
        manifest = json.loads((ROOT / "extension/manifest.json").read_text(encoding="utf-8"))

        self.assertTrue((ROOT / "extension" / manifest["server"]["entry_point"]).exists())
        self.assertTrue((ROOT / "extension" / manifest["icon"]).exists())
        self.assertTrue(manifest["user_config"]["folders"]["required"])


if __name__ == "__main__":
    unittest.main()
