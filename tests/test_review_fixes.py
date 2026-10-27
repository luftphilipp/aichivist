"""Edge cases found in the review: each test pins down one fixed weakness."""
import contextlib
import io
import json
import unittest
from pathlib import Path
from unittest import mock

from aichivist import bagit, catalog, cli, fileops, guard, inventory, journal, lifecycle, plan, undo
from helpers import SandboxTest


def run(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = cli.main(list(args))
    return code, out.getvalue()


class ClosedCollectionEdgesTest(SandboxTest):
    def test_moving_a_parent_folder_does_not_carry_a_closed_collection_away(self):
        self.make_file("Study/Term 1/notes.md")
        lifecycle.close(self.root / "Study/Term 1")
        (self.root / "Archive").mkdir()

        with self.assertRaises(fileops.FilingError):
            fileops.move(self.root / "Study", self.root / "Archive/Study")
        with self.assertRaises(fileops.FilingError):
            fileops.trash(self.root / "Study")

    def test_filing_next_to_a_closed_collection_is_allowed(self):
        self.make_file("Study/Term 1/notes.md")
        lifecycle.close(self.root / "Study/Term 1")
        new = self.make_file("Downloads/plan of study.pdf")

        fileops.move(new, self.root / "Study/plan of study.pdf")

        self.assertTrue((self.root / "Study/plan of study.pdf").exists())

    def test_closing_a_folder_that_contains_a_closed_collection_is_refused(self):
        self.make_file("Study/Term 1/notes.md")
        lifecycle.close(self.root / "Study/Term 1")

        with self.assertRaises(fileops.FilingError):
            lifecycle.close(self.root / "Study")


class UndoEdgesTest(SandboxTest):
    def test_last_counts_file_steps_only(self):
        a = self.make_file("inbox/a.pdf")
        fileops.move(a, self.root / "inbox/b.pdf")
        journal.write("", self.root, "protect")
        journal.write("", self.root / "plan.md", "apply_plan")

        undo.undo(last=1)

        self.assertTrue(a.exists())

    def test_second_undo_does_not_repeat_steps(self):
        a = self.make_file("inbox/a.pdf")
        fileops.move(a, self.root / "inbox/b.pdf")
        undo.undo(last=1)

        skipped = undo.undo(last=1)

        self.assertEqual(skipped, [])
        self.assertTrue(a.exists())


class ErrorReportingTest(SandboxTest):
    def test_os_errors_become_clear_messages_not_tracebacks(self):
        folder = self.root / "box"
        self.make_file("box/a.pdf")

        code, out = run("mv", str(folder), str(folder / "inside"))

        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", out)
        self.assertIn("error", out.lower())

    def test_failed_cross_drive_copy_leaves_no_half_copy(self):
        src = self.make_file("inbox/a.pdf", b"data")
        dst = self.root / "drive/a.pdf"
        dst.parent.mkdir()
        exdev = OSError(18, "cross-device")
        with mock.patch("aichivist.fileops.os.rename", side_effect=exdev), \
                mock.patch("aichivist.fileops.shutil.copyfile", side_effect=OSError(28, "disk full")), \
                self.assertRaises(OSError):
            fileops.move(src, dst)

        self.assertTrue(src.exists())
        self.assertFalse(dst.exists())


class BagEdgesTest(SandboxTest):
    def test_export_refuses_a_collection_that_changed_since_closing(self):
        self.make_file("T1/a.pdf", b"a")
        lifecycle.close(self.root / "T1")
        (self.root / "T1/a.pdf").unlink()

        with self.assertRaises(fileops.FilingError):
            bagit.export(self.root / "T1", self.root / "bag")
        self.assertFalse((self.root / "bag").exists())

    def test_multiline_note_does_not_break_bag_info(self):
        self.make_file("T1/a.pdf", b"a")
        lifecycle.close(self.root / "T1", note="line one\nline two")

        bagit.export(self.root / "T1", self.root / "bag")

        info = (self.root / "bag/bag-info.txt").read_text(encoding="utf-8")
        self.assertIn("External-Description: line one line two\n", info)


class GuardEdgesTest(unittest.TestCase):
    def setUp(self):
        self.protected = [Path("/home/alex/Personal")]

    def blocked(self, command):
        return guard.check_command(command, self.protected) is not None

    def test_overwriting_redirect_is_blocked(self):
        self.assertTrue(self.blocked("echo x > /home/alex/Personal/contract.pdf"))
        self.assertFalse(self.blocked("cat /home/alex/Personal/_catalog.md > /tmp/copy.md"))

    def test_pipelines_into_xargs_rm_are_blocked(self):
        self.assertTrue(self.blocked("find /home/alex/Personal -name '*.tmp' | xargs rm"))

    def test_copying_into_a_protected_area_is_blocked_reading_out_is_not(self):
        self.assertTrue(self.blocked("cp /tmp/new.pdf /home/alex/Personal/new.pdf"))
        self.assertFalse(self.blocked("cp /home/alex/Personal/a.pdf /tmp/backup.pdf"))
        self.assertTrue(self.blocked("rsync -a --remove-source-files /home/alex/Personal/ /tmp/x/"))

    def test_powershell_tool_is_checked_too(self):
        payload = {"tool_name": "PowerShell", "tool_input": {"command": "Remove-Item C:/Users/alex/Personal/a.pdf"}}
        with mock.patch("sys.stdin", io.StringIO(json.dumps(payload))), \
                mock.patch.object(guard.protect, "listed", return_value=[Path("C:/Users/alex/Personal")]), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(guard.main(), 2)


class PlanEdgesTest(SandboxTest):
    def test_reads_tables_reformatted_by_an_editor(self):
        src = self.make_file("Downloads/a.pdf")
        f = self.make_file("plan.md", (
            "# Plan\n\n|  ✓  | Source | Target | Reason |\n| :-- | :--- | :--- | :--- |\n"
            f"|  x  | {src} | {self.root}/A.pdf | padded |\n").encode())

        rows = plan.read(f)

        self.assertEqual([(r.mark, r.reason) for r in rows], [("x", "padded")])

    def test_same_source_twice_is_reported(self):
        src = self.make_file("Downloads/a.pdf")
        (self.root / "A").mkdir()
        f = self.root / "plan.md"
        plan.add(f, src, self.root / "A/one.pdf", "one")
        plan.add(f, src, self.root / "A/two.pdf", "two")

        self.assertIn("same source", plan.check(f)[1][1])


class CatalogEdgesTest(SandboxTest):
    def test_add_missing_twice_keeps_one_to_describe_section(self):
        self.make_file("Area/_catalog.md", b"| File | Content |\n|---|---|\n")
        self.make_file("Area/a.pdf")
        catalog.add_missing(self.root / "Area/_catalog.md")
        self.make_file("Area/b.pdf")
        catalog.add_missing(self.root / "Area/_catalog.md")

        text = (self.root / "Area/_catalog.md").read_text(encoding="utf-8")
        self.assertEqual(text.count("## To describe"), 1)
        self.assertIn("| b.pdf |", text)

    def test_catalogs_of_sub_areas_are_not_records(self):
        self.make_file("Area/_catalog.md", b"| File | Content |\n|---|---|\n| Sub/x.pdf | x |\n")
        self.make_file("Area/Sub/x.pdf")
        self.make_file("Area/Sub/_catalog.md")

        self.assertTrue(catalog.check(self.root / "Area/_catalog.md").ok)


class InventoryEntriesTest(SandboxTest):
    def test_json_always_lists_the_files_of_an_inbox(self):
        self.make_file("Downloads/a.pdf")
        run("inventory", str(self.root / "Downloads"), "--save")

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(["--json", "inventory", str(self.root / "Downloads")])

        # agents read stdout only; warnings on stderr must not break the JSON
        self.assertEqual(json.loads(out.getvalue())["data"]["entries"], ["a.pdf"],
                         f"exit {code}, stderr: {err.getvalue()}")

    def test_first_run_lists_entries_too(self):
        self.make_file("Downloads/a.pdf")

        changes = inventory.diff(self.root / "Downloads")

        self.assertEqual(changes.entries, ["a.pdf"])


if __name__ == "__main__":
    unittest.main()
