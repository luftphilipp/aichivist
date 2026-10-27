import unittest
from unittest import mock

from aichivist import update
from aichivist.commands import cmd_update
from helpers import SandboxTest


class Args:
    check = False


class UpdateTest(SandboxTest):
    def test_red_or_running_tests_keep_the_installed_version(self):
        with mock.patch.object(update, "latest", return_value=update.Latest("abc1234", False, "failure")), \
                mock.patch.object(update, "install") as install:
            out = cmd_update(Args())

        install.assert_not_called()
        self.assertEqual(out.code, 1)
        self.assertIn("keeping the installed one", out.lines[0])

    def test_green_tests_install_exactly_that_commit(self):
        with mock.patch.object(update, "latest", return_value=update.Latest("abc1234def", True, "success")), \
                mock.patch.object(update, "install", return_value=0) as install:
            out = cmd_update(Args())

        install.assert_called_once_with("abc1234def")
        self.assertIn("abc1234", out.lines[0])

    def test_latest_reads_the_newest_run_on_main(self):
        answer = mock.MagicMock()
        answer.__enter__.return_value.read.return_value = (
            b'{"workflow_runs": [{"head_sha": "f00", "status": "completed", "conclusion": "success"}]}')
        with mock.patch.object(update, "_token", return_value=None), \
                mock.patch.object(update.urllib.request, "urlopen", return_value=answer), \
                mock.patch.object(update.json, "load", side_effect=lambda r: __import__("json").loads(r.read())):
            self.assertEqual(update.latest(), update.Latest("f00", True, "success"))


if __name__ == "__main__":
    unittest.main()
