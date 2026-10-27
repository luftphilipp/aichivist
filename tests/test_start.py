import unittest
from unittest import mock

from aichivist import start, survey
from helpers import SandboxTest


class StartMenuTest(SandboxTest):
    def run_menu(self, *answers):
        said = []
        with mock.patch.object(start, "survey", wraps=survey) as wrapped, \
                mock.patch.object(survey.drives, "health", return_value=survey.drives.UNKNOWN):
            code = start.menu(ask=mock.Mock(side_effect=list(answers)), say=said.append)
        return code, "\n".join(said), wrapped

    def test_looking_at_a_folder_reports_and_changes_nothing(self):
        self.make_file("Inbox/scan_0042.pdf")

        code, text, _ = self.run_menu("2", str(self.root / "Inbox"), "0")

        self.assertEqual(code, 0)
        self.assertIn("unclear names", text)
        self.assertTrue((self.root / "Inbox/scan_0042.pdf").exists())

    def test_wrong_input_and_missing_folders_are_explained_not_fatal(self):
        code, text, _ = self.run_menu("9", "2", str(self.root / "nowhere"), "0")

        self.assertIn("Please type a number", text)
        self.assertIn("Not a folder", text)
        self.assertEqual(code, 0)

    def test_closing_the_window_ends_quietly(self):
        code, _, _ = self.run_menu(EOFError())

        self.assertEqual(code, 0)

    def test_ai_option_explains_the_steps_in_the_window(self):
        _, text, _ = self.run_menu("6", "0")

        self.assertIn("Claude Desktop", text)
        self.assertIn("nothing is moved before you say yes", text)

    def test_ai_option_shows_only_the_way_for_the_installed_app(self):
        with mock.patch.object(start, "installed_ai", return_value=["Claude Code"]):
            _, text, _ = self.run_menu("6", "0")

        self.assertIn("/plugin marketplace add", text)
        self.assertNotIn(".mcpb", text)

    def test_without_an_ai_app_claude_desktop_is_recommended_with_its_download(self):
        with mock.patch.object(start, "installed_ai", return_value=[]):
            _, text, _ = self.run_menu("6", "0")

        self.assertIn("claude.ai/download", text)
        self.assertNotIn("/plugin", text)

    def test_after_looking_the_next_step_points_to_the_ai_option(self):
        _, text, _ = self.run_menu("2", str(self.root), "0")

        self.assertIn("choose 6", text)

    def test_installed_apps_are_found_by_their_usual_places(self):
        app = self.root / "Applications/Claude.app"
        app.mkdir(parents=True)
        with mock.patch.object(start, "DESKTOP_PLACES", [app]), mock.patch.object(start.shutil, "which",
                                                                                   return_value=None):
            self.assertEqual(start.installed_ai(), ["Claude Desktop"])

    def test_installing_asks_first(self):
        with mock.patch.object(start.subprocess, "run") as run:
            self.run_menu("7", "n", "0")

        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
