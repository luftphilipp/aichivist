import unittest

from aichivist import fileops, inventory, journal, undo
from helpers import SandboxTest


class InventoryTest(SandboxTest):
    def test_first_run_reports_everything_as_baseline(self):
        self.make_file("inbox/a.pdf")

        changes = inventory.diff(self.root / "inbox", save=True)

        self.assertTrue(changes.first_run)

    def test_detects_new_changed_moved_and_removed(self):
        inbox = self.root / "inbox"
        self.make_file("inbox/keep.pdf", b"keep")
        self.make_file("inbox/edit.txt", b"v1")
        self.make_file("inbox/old/moved.pdf", b"same bytes")
        self.make_file("inbox/gone.pdf", b"gone")
        inventory.diff(inbox, save=True)

        (inbox / "edit.txt").write_bytes(b"version 2")
        (inbox / "old/moved.pdf").rename(inbox / "moved.pdf")
        (inbox / "gone.pdf").unlink()
        self.make_file("inbox/new.pdf", b"new")
        changes = inventory.diff(inbox, save=False)

        self.assertEqual(changes.new, ["new.pdf"])
        self.assertEqual(changes.changed, ["edit.txt"])
        self.assertEqual(changes.moved, [("old/moved.pdf", "moved.pdf")])
        self.assertEqual(changes.removed, ["gone.pdf"])

    def test_project_folders_are_treated_as_one_unit(self):
        self.make_file("area/my-project/.git/HEAD", b"ref")
        self.make_file("area/my-project/src/main.py", b"print()")

        changes = inventory.diff(self.root / "area", save=True)

        self.assertEqual(changes.entries, ["my-project/"])


class UndoTest(SandboxTest):
    def test_undo_restores_moves_in_reverse_order(self):
        a = self.make_file("inbox/a.pdf")
        (self.root / "archive").mkdir()
        fileops.move(a, self.root / "archive/a.pdf")
        fileops.move(self.root / "archive/a.pdf", self.root / "archive/A renamed.pdf")

        undo.undo()

        self.assertTrue(a.exists())
        self.assertFalse((self.root / "archive/A renamed.pdf").exists())

    def test_undo_restores_trashed_file_and_removes_created_empty_folder(self):
        f = self.make_file("archive/dup.pdf")
        fileops.trash(f)
        moved = self.make_file("inbox/b.pdf")
        fileops.move(moved, self.root / "fresh/b.pdf", create_folder=True)

        undo.undo()

        self.assertTrue(f.exists())
        self.assertTrue(moved.exists())
        self.assertFalse((self.root / "fresh").exists())

    def test_undo_since_only_reverts_later_steps(self):
        first = self.make_file("inbox/1.pdf")
        fileops.move(first, self.root / "inbox/one.pdf")
        cutoff = journal.read()[-1].time
        second = self.make_file("inbox/2.pdf")
        fileops.move(second, self.root / "inbox/two.pdf")

        undo.undo(since=cutoff, inclusive=False)

        self.assertTrue((self.root / "inbox/one.pdf").exists())
        self.assertTrue(second.exists())

    def test_undo_skips_when_state_no_longer_matches(self):
        a = self.make_file("inbox/a.pdf")
        fileops.move(a, self.root / "inbox/b.pdf")
        (self.root / "inbox/b.pdf").unlink()

        skipped = undo.undo()

        self.assertEqual(len(skipped), 1)


if __name__ == "__main__":
    unittest.main()
