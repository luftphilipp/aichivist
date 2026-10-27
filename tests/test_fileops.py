import errno
import unittest
from unittest import mock

from aichivist import fileops, journal
from helpers import SandboxTest


class MoveTest(SandboxTest):
    def test_moves_file_and_logs_it(self):
        src = self.make_file("inbox/Unknown.pdf", b"pass statement")
        dst = self.root / "archive/2026-09-21 Example Rail Statement.pdf"
        dst.parent.mkdir()

        fileops.move(src, dst)

        self.assertFalse(src.exists())
        self.assertEqual(dst.read_bytes(), b"pass statement")
        self.assertEqual([e.action for e in journal.read()], ["move"])

    def test_rename_in_same_folder_is_logged_as_rename(self):
        src = self.make_file("inbox/voucher2.pdf")

        fileops.move(src, self.root / "inbox/Example Store Gift Card 100.pdf")

        self.assertEqual(journal.read()[0].action, "rename")

    def test_never_overwrites_existing_target(self):
        src = self.make_file("inbox/a.pdf", b"new")
        dst = self.make_file("archive/a.pdf", b"old")

        with self.assertRaises(fileops.FilingError):
            fileops.move(src, dst)

        self.assertEqual(dst.read_bytes(), b"old")
        self.assertTrue(src.exists())

    def test_refuses_missing_target_folder_unless_allowed(self):
        src = self.make_file("inbox/a.pdf")
        dst = self.root / "new/folder/a.pdf"

        with self.assertRaises(fileops.FilingError):
            fileops.move(src, dst)
        fileops.move(src, dst, create_folder=True)

        self.assertTrue(dst.exists())
        self.assertEqual([e.action for e in journal.read()], ["folder_created", "move"])

    def test_cross_drive_move_copies_verifies_and_removes_source(self):
        folder = self.root / "inbox/photos"
        self.make_file("inbox/photos/sub/a.jpg", b"x" * 500)
        self.make_file("inbox/photos/b.jpg", b"y" * 10)
        dst = self.root / "drive/photos"
        dst.parent.mkdir()
        exdev = OSError(errno.EXDEV, "cross-device link")

        with mock.patch("aichivist.fileops.os.rename", side_effect=exdev):
            fileops.move(folder, dst)

        self.assertFalse(folder.exists())
        self.assertEqual((dst / "sub/a.jpg").read_bytes(), b"x" * 500)

    def test_cross_drive_move_keeps_source_when_copy_differs(self):
        src = self.make_file("inbox/a.pdf", b"original")
        dst = self.root / "drive/a.pdf"
        dst.parent.mkdir()
        exdev = OSError(errno.EXDEV, "cross-device link")

        with mock.patch("aichivist.fileops.os.rename", side_effect=exdev), \
                mock.patch("aichivist.fileops.same_content", return_value=False), \
                self.assertRaises(fileops.FilingError):
            fileops.move(src, dst)

        self.assertTrue(src.exists())


class TrashTest(SandboxTest):
    def test_moves_to_trash_without_overwriting(self):
        self.make_file("trash/dup.pdf", b"older trash")
        src = self.make_file("archive/dup.pdf", b"duplicate")

        target = fileops.trash(src)

        self.assertFalse(src.exists())
        self.assertEqual(target.name, "dup (1).pdf")
        self.assertEqual((self.trash / "dup.pdf").read_bytes(), b"older trash")
        self.assertEqual(journal.read()[0].action, "trash")


class FreedesktopTrashTest(SandboxTest):
    def setUp(self):
        super().setUp()
        import os
        self.files = self.root / "share" / "Trash" / "files"
        os.environ["AICHIVIST_TRASH"] = str(self.files)

    def test_trash_writes_trashinfo_so_file_managers_can_restore(self):
        src = self.make_file("archive/Old report.pdf")

        target = fileops.trash(src)

        info = (self.files.parent / "info" / f"{target.name}.trashinfo").read_text(encoding="utf-8")
        self.assertTrue(info.startswith("[Trash Info]\nPath="))
        self.assertIn("Old%20report.pdf", info)
        self.assertIn("DeletionDate=", info)

    def test_undo_removes_the_trashinfo(self):
        from aichivist import undo
        src = self.make_file("archive/a.pdf")
        target = fileops.trash(src)

        undo.undo(last=1)

        self.assertTrue(src.exists())
        self.assertFalse((self.files.parent / "info" / f"{target.name}.trashinfo").exists())

    def test_other_trash_folders_get_no_trashinfo(self):
        import os
        os.environ["AICHIVIST_TRASH"] = str(self.trash)
        fileops.trash(self.make_file("archive/b.pdf"))

        self.assertFalse((self.trash.parent / "info").exists())


if __name__ == "__main__":
    unittest.main()
