import contextlib
import io
import unittest

from aichivist import cli, journal
from helpers import SandboxTest


def run(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = cli.main(list(args))
    return code, out.getvalue()


class CliTest(SandboxTest):
    def test_mv_moves_and_reports(self):
        src = self.make_file("inbox/a.pdf")
        (self.root / "archive").mkdir()

        code, out = run("mv", str(src), str(self.root / "archive/a.pdf"))

        self.assertEqual(code, 0)
        self.assertIn("->", out)

    def test_rule_violation_exits_with_error_and_changes_nothing(self):
        src = self.make_file("inbox/a.pdf", b"new")
        dst = self.make_file("archive/a.pdf", b"old")

        code, out = run("mv", str(src), str(dst))

        self.assertEqual(code, 1)
        self.assertIn("nothing overwritten", out)
        self.assertEqual(journal.read(), [])

    def test_undo_requires_an_explicit_scope(self):
        code, _ = run("undo")

        self.assertEqual(code, 2)

    def test_undo_last_reverts_one_step(self):
        src = self.make_file("inbox/a.pdf")
        run("mv", str(src), str(self.root / "inbox/b.pdf"))

        code, out = run("undo", "--last", "1")

        self.assertEqual(code, 0)
        self.assertTrue(src.exists())
        self.assertIn("1 step(s) undone", out)
        self.assertIn("nothing to undo", run("undo", "--last", "1")[1])

    def test_close_status_and_verify(self):
        self.make_file("Study/Semester 1/notes.pdf")
        area = str(self.root / "Study/Semester 1")

        self.assertEqual(run("close", area, "--note", "done")[0], 0)
        code, out = run("status", area)
        self.assertIn("closed", out)
        code, out = run("verify", area)
        self.assertEqual(code, 0)
        self.assertIn("intact", out)

    def test_check_catalog_reports_gaps_with_error_code(self):
        self.make_file("Area/_catalog.md", b"| File | Content |\n|---|---|\n| listed.pdf | x |\n")
        self.make_file("Area/listed.pdf")
        self.make_file("Area/unlisted.pdf")

        code, out = run("check-catalog", str(self.root / "Area/_catalog.md"))

        self.assertEqual(code, 1)
        self.assertIn("NOT IN CATALOG\tunlisted.pdf", out)

    def test_duplicates_lists_pairs_with_error_code(self):
        self.make_file("archive/kept.pdf", b"same")
        new = self.make_file("Downloads/copy.pdf", b"same")

        code, out = run("duplicates", str(new), "--in", str(self.root / "archive"))

        self.assertEqual(code, 1)
        self.assertIn("DUPLICATE", out)
        self.assertIn("kept.pdf", out)

    def test_close_then_search_in_closed_collection(self):
        self.make_file("Study/T1/notes.md", b"median and mode")
        area = str(self.root / "Study/T1")
        run("close", area)

        code, out = run("search", area, "median")

        self.assertEqual(code, 0)
        self.assertIn("notes.md", out)

    def test_search_in_open_collection_is_refused(self):
        (self.root / "Open").mkdir()

        self.assertEqual(run("search", str(self.root / "Open"), "x")[0], 1)

    def test_check_catalog_add_missing(self):
        self.make_file("Area/_catalog.md", b"| File | Content |\n|---|---|\n")
        self.make_file("Area/new.pdf")

        code, out = run("check-catalog", str(self.root / "Area/_catalog.md"), "--add-missing")

        self.assertEqual(code, 0)
        self.assertIn("ADDED\tnew.pdf", out)

    def test_json_output_for_agents(self):
        import json
        self.make_file("archive/kept.pdf", b"same")
        new = self.make_file("Downloads/copy.pdf", b"same")

        code, out = run("--json", "duplicates", str(new), "--in", str(self.root / "archive"))

        result = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual(result["command"], "duplicates")
        self.assertTrue(result["data"][0]["match"].endswith("kept.pdf"))

    def test_json_error_is_machine_readable(self):
        import json
        src = self.make_file("inbox/a.pdf")
        dst = self.make_file("archive/a.pdf")

        code, out = run("--json", "mv", str(src), str(dst))

        self.assertEqual(code, 1)
        self.assertFalse(json.loads(out)["ok"])
        self.assertIn("nothing overwritten", json.loads(out)["error"])

    def test_plan_workflow(self):
        plan_file = str(self.root / "plan.md")
        src = self.make_file("Downloads/a.pdf")
        (self.root / "archive").mkdir()

        run("plan", "add", plan_file, str(src), str(self.root / "archive/A.pdf"), "--reason", "test")
        self.assertEqual(run("plan", "check", plan_file)[0], 0)
        run("plan", "approve", plan_file)
        code, out = run("plan", "apply", plan_file)

        self.assertEqual(code, 0)
        self.assertIn("1 done", out)
        self.assertTrue((self.root / "archive/A.pdf").exists())

    def test_inventory_marks_moves_by_hand(self):
        area = self.root / "area"
        self.make_file("area/a.pdf", b"a")
        (area / "sub").mkdir()
        run("inventory", str(area), "--save")
        (area / "a.pdf").rename(area / "sub/a.pdf")

        code, out = run("inventory", str(area))

        self.assertIn("MOVED BY HAND", out)

    def test_protect_and_export_bag(self):
        self.make_file("T1/notes.md", b"x")
        self.assertEqual(run("protect", str(self.root / "T1"))[0], 0)
        self.assertIn(str(self.root / "T1"), run("protected")[1])
        run("close", str(self.root / "T1"))

        self.assertEqual(run("export-bag", str(self.root / "T1"), str(self.root / "bag"))[0], 0)
        code, out = run("validate-bag", str(self.root / "bag"))
        self.assertEqual(code, 0)
        self.assertIn("valid", out)

    def test_survey_reports_without_changing_anything(self):
        self.make_file("Downloads/Unknown.pdf", b"x")
        self.make_file("Downloads/copy of x.pdf", b"x")
        before = sorted(p.name for p in (self.root / "Downloads").iterdir())

        code, out = run("survey", str(self.root / "Downloads"))

        self.assertEqual(code, 0)
        self.assertIn("1 duplicate file in 1 group", out)
        self.assertEqual(sorted(p.name for p in (self.root / "Downloads").iterdir()), before)

    def test_inventory_lists_new_files(self):
        inbox = self.root / "inbox"
        inbox.mkdir()
        run("inventory", str(inbox), "--save")
        self.make_file("inbox/new.pdf")

        code, out = run("inventory", str(inbox))

        self.assertEqual(code, 0)
        self.assertIn("NEW\tnew.pdf", out)


if __name__ == "__main__":
    unittest.main()
