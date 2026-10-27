"""Each command once through the command line: exit code and the line a person reads."""
import contextlib
import io
import json
import unittest
from unittest import mock

from test_photos import jpeg_taken
from test_similar_describe_style import POLICY

from aichivist import cli, schedule
from helpers import SandboxTest


def run(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = cli.main(list(args))
    return code, out.getvalue()


class FileCommandsTest(SandboxTest):
    def test_trash_and_note(self):
        f = self.make_file("inbox/old.pdf")

        self.assertEqual(run("trash", str(f))[0], 0)
        self.assertFalse(f.exists())
        self.assertEqual(run("note", "renamed_by_hand", "a", "b"), (0, "logged\n"))

    def test_apps_names_what_depends_on_a_path(self):
        project = self.make_file("Code/tool/pyproject.toml").parent

        code, out = run("apps", str(project), str(self.make_file("letter.pdf")))

        self.assertEqual(code, 0)
        self.assertIn("code project", out)
        self.assertIn("no program depends on it", out)

    def test_photos_lists_and_proposes(self):
        self.make_file("inbox/IMG_0001.jpg", jpeg_taken())
        plan_file = self.root / "plan.md"

        code, out = run("photos", str(self.root / "inbox"), "--to", str(self.root / "Photos"), "--plan", str(plan_file))

        self.assertEqual(code, 0)
        self.assertIn("2021-07-14", out)
        self.assertIn("IMG_0001.jpg", plan_file.read_text(encoding="utf-8"))

    def test_similar_suggest_and_style(self):
        self.make_file("a/policy.txt", POLICY.encode())
        self.make_file("b/policy scan.txt", (POLICY + " Page 1").encode())

        self.assertEqual(run("similar", str(self.root / "b"), "--in", str(self.root / "a"))[0], 1)
        self.assertIn("suggested_name: 2026-01-01 Example Health AG",
                      run("suggest", str(self.root / "a/policy.txt"))[1])
        self.assertIn("policy.txt", run("style", str(self.root / "a"))[1])


class AreaCommandsTest(SandboxTest):
    def test_structure_and_due(self):
        self.make_file("Area/Lonely/one.pdf")

        self.assertIn("only 1 file(s)", run("structure", str(self.root / "Area"))[1])
        code, out = run("due", str(self.root / "Area"), "--years", "0")
        self.assertEqual(code, 0)
        self.assertIn("one.pdf", out)

    def test_storage_shows_the_format_first_then_checks(self):
        table = self.root / "storage.md"

        code, out = run("storage", str(table))
        self.assertEqual(code, 1)
        self.assertIn("| Place | Kind |", out)

        table.write_text("| Place | Kind | Where | Holds | Price | Per |\n|---|---|---|---|---|---|\n"
                         "| Cloud | cloud | away | Docs | 3 | month |\n", encoding="utf-8")
        self.assertIn("only in the cloud", run("storage", str(table), "--currency", "CHF")[1])

    def test_catalog_page_and_check_rules(self):
        self.make_file("Area/_catalog.md", b"| File | Content |\n|---|---|\n| a.pdf | x |\n")

        self.assertIn("catalog page:", run("catalog-page", str(self.root / "Area"), "--out",
                                           str(self.root / "page.html"))[1])
        rules = self.make_file("rules.md", b"Owner: <your name>\n")
        code, out = run("check-rules", str(rules))
        self.assertEqual((code, "<your name>" in out), (1, True))

    def test_reopen_and_unprotect(self):
        folder = self.make_file("Term/notes.md").parent
        run("close", str(folder))

        self.assertIn("open", run("reopen", str(folder), "--note", "late grade")[1])
        run("protect", str(folder))
        self.assertEqual(run("unprotect", str(folder))[0], 0)

    def test_plan_review_returns_the_page_address(self):
        plan_file = self.root / "plan.md"
        run("plan", "add", str(plan_file), str(self.make_file("a.pdf")), "TRASH", "--reason", "duplicate")

        with mock.patch("aichivist.review.serve", return_value="http://127.0.0.1:1/"):
            self.assertIn("127.0.0.1", run("plan", "review", str(plan_file))[1])


class WatchCommandTest(SandboxTest):
    def test_reminder_only_from_the_threshold(self):
        inbox = self.make_file("Downloads/a.pdf").parent

        with mock.patch("aichivist.notify.show") as show:
            self.assertEqual(run("watch", str(inbox), "--threshold", "5")[0], 0)
            self.assertEqual(run("watch", str(inbox), "--threshold", "1")[0], 3)
        show.assert_called_once()

    def test_install_and_uninstall_use_the_system_scheduler(self):
        inbox = self.make_file("Downloads/a.pdf").parent
        with mock.patch.object(schedule.Path, "home", return_value=self.root), \
                mock.patch.object(schedule, "_run", return_value=0):
            code, out = run("watch", str(inbox), "--install", "--at", "08:15")
            self.assertEqual(code, 0)
            self.assertIn("daily at 08:15", out)
            self.assertEqual(run("watch", "--uninstall")[0], 0)

    def test_wrong_time_and_missing_inbox_are_explained(self):
        self.assertEqual(run("watch")[0], 2)
        code, out = run("watch", str(self.root), "--install", "--at", "9am")
        self.assertEqual(code, 2)
        self.assertIn("HH:MM", out)

    def test_json_output_for_agents(self):
        inbox = self.make_file("Downloads/a.pdf").parent

        data = json.loads(run("--json", "watch", str(inbox), "--threshold", "5")[1])

        self.assertEqual(data["data"][0]["files"], 1)


if __name__ == "__main__":
    unittest.main()
