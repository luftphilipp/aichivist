import contextlib
import io
import json
import unittest
from pathlib import Path
from unittest import mock

from aichivist import guard, protect
from helpers import SandboxTest


class GuardRuleTest(unittest.TestCase):
    def setUp(self):
        self.protected = [Path("/home/alex/Documents/Personal")]

    def blocked(self, command):
        return guard.check_command(command, self.protected) is not None

    def test_blocks_raw_moves_and_deletes_in_protected_areas(self):
        self.assertTrue(self.blocked('mv "/home/alex/Documents/Personal/a.pdf" /tmp/a.pdf'))
        self.assertTrue(self.blocked("rm -rf /home/alex/Documents/Personal/Insurance"))
        self.assertTrue(self.blocked("cd /tmp && rm /home/alex/Documents/Personal/x.pdf"))
        self.assertTrue(self.blocked("find /home/alex/Documents/Personal -name '*.tmp' -delete"))
        self.assertTrue(self.blocked("python3 -c \"import os; os.remove('/home/alex/Documents/Personal/a')\""))
        self.assertTrue(self.blocked(r"mv /home/alex/Documents/Personal/My\ File.pdf /tmp/"))

    def test_allows_aichivist_reading_and_other_folders(self):
        self.assertFalse(self.blocked('aichivist mv "/home/alex/Documents/Personal/a.pdf" "/home/alex/x.pdf"'))
        self.assertFalse(self.blocked("ls -la /home/alex/Documents/Personal"))
        self.assertFalse(self.blocked("cat /home/alex/Documents/Personal/_catalog.md"))
        self.assertFalse(self.blocked("rm /tmp/scratch.txt"))
        self.assertFalse(self.blocked("mv /home/alex/Documents/PersonalNotes/a /tmp/"))

    def test_home_shortcut_is_recognised(self):
        with mock.patch.object(guard.Path, "home", return_value=Path("/home/alex")):
            self.assertTrue(self.blocked("rm ~/Documents/Personal/a.pdf"))


class GuardHookTest(SandboxTest):
    def run_hook(self, payload):
        err = io.StringIO()
        with mock.patch("sys.stdin", io.StringIO(json.dumps(payload))), contextlib.redirect_stderr(err):
            code = guard.main()
        return code, err.getvalue()

    def test_hook_blocks_with_exit_code_2_and_explains(self):
        area = self.root / "Personal"
        area.mkdir()
        protect.add(area)

        code, message = self.run_hook({"tool_name": "Bash", "tool_input": {"command": f"rm {area}/a.pdf"}})

        self.assertEqual(code, 2)
        self.assertIn("aichivist", message)

    def test_hook_ignores_other_tools_and_unprotected_setups(self):
        self.assertEqual(self.run_hook({"tool_name": "Read", "tool_input": {"file_path": "/x"}})[0], 0)
        self.assertEqual(self.run_hook({"tool_name": "Bash", "tool_input": {"command": "rm /tmp/x"}})[0], 0)

    def test_protect_list_is_kept_without_duplicates(self):
        area = self.root / "Personal"
        area.mkdir()

        protect.add(area)
        protect.add(area)
        self.assertEqual(protect.listed(), [area])
        protect.remove(area)
        self.assertEqual(protect.listed(), [])


if __name__ == "__main__":
    unittest.main()
