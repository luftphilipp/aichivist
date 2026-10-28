"""The Claude plugin as Anthropic's directory checks it: manifest, privacy policy, pinned server, hook script."""
import json
import os
import re
import unittest
from pathlib import Path

import aichivist

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin"
MIN_README_WORDS = 40  # the directory refuses shorter plugin READMEs
SYSTEM_FILES = {".DS_Store", "Thumbs.db", "desktop.ini"}


def manifest():
    return json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))


class PluginManifestTest(unittest.TestCase):
    def test_listing_fields_are_set(self):
        m = manifest()

        self.assertEqual(m["version"], aichivist.__version__)
        self.assertEqual(m["license"], "MIT")
        for field in ("privacyPolicyUrl", "documentationUrl", "supportUrl", "homepage"):
            self.assertTrue(m[field].startswith("https://"), field)
        self.assertTrue((PLUGIN / m["icon"]).is_file())

    def test_mcp_server_runs_the_released_version_pinned(self):
        server = manifest()["mcpServers"]["aichivist"]

        self.assertEqual(server["command"], "uvx")
        self.assertIn(f"aichivist[mcp]=={aichivist.__version__}", server["args"])
        options = set(manifest()["userConfig"])
        for ref in re.findall(r"\$\{user_config\.(\w+)\}", " ".join(server["args"])):
            self.assertIn(ref, options)

    def test_readme_explains_it_and_has_a_privacy_policy(self):
        text = (PLUGIN / "README.md").read_text(encoding="utf-8")
        prose = re.sub(r"```.*?```", "", text, flags=re.DOTALL)

        self.assertGreaterEqual(len(prose.split()), MIN_README_WORDS)
        self.assertIn("## Privacy Policy", text)
        self.assertIn("## Privacy Policy", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertTrue((ROOT / "PRIVACY.md").is_file())

    def test_hook_runs_a_script_inside_the_plugin(self):
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        command = hooks["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        script = PLUGIN / command.replace('"${CLAUDE_PLUGIN_ROOT}"/', "")

        self.assertTrue(command.startswith('"${CLAUDE_PLUGIN_ROOT}"/'))
        self.assertTrue(script.is_file())
        if os.name != "nt":
            self.assertTrue(os.access(script, os.X_OK))

    def test_no_system_files_in_the_plugin(self):
        self.assertEqual([p for p in PLUGIN.rglob("*") if p.name in SYSTEM_FILES], [])


if __name__ == "__main__":
    unittest.main()
