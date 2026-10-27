import unittest

from aichivist import fileops, journal, lifecycle, undo
from helpers import SandboxTest


class LifecycleTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.area = self.root / "Study/Semester 1"
        self.make_file("Study/Semester 1/Statistics/slides.pdf", b"slides")
        self.make_file("Study/Semester 1/Python/exercise.ipynb", b"{}")

    def test_new_area_is_open(self):
        self.assertEqual(lifecycle.status(self.area).state, "open")

    def test_close_records_fixity_manifest(self):
        lifecycle.close(self.area, note="all grades received")

        info = lifecycle.status(self.area)
        self.assertEqual(info.state, "closed")
        self.assertEqual(info.file_count, 2)
        self.assertEqual(journal.read()[-1].action, "close")

    def test_closed_area_blocks_moves_in_and_out(self):
        lifecycle.close(self.area)
        inbox_file = self.make_file("Downloads/late.pdf")

        with self.assertRaises(fileops.FilingError):
            fileops.move(inbox_file, self.area / "Statistics/late.pdf")
        with self.assertRaises(fileops.FilingError):
            fileops.move(self.area / "Statistics/slides.pdf", self.root / "Downloads/slides.pdf")
        with self.assertRaises(fileops.FilingError):
            fileops.trash(self.area / "Python/exercise.ipynb")

    def test_subfolder_of_closed_area_is_closed_too(self):
        lifecycle.close(self.area)

        self.assertEqual(lifecycle.status(self.area / "Statistics").state, "closed")

    def test_reopen_allows_changes_again(self):
        lifecycle.close(self.area)
        lifecycle.reopen(self.area, note="late grade report")
        late = self.make_file("Downloads/grade.pdf")

        fileops.move(late, self.area / "Statistics/grade.pdf")

        self.assertEqual(lifecycle.status(self.area).state, "open")

    def test_verify_detects_changed_missing_and_extra_files(self):
        lifecycle.close(self.area)
        (self.area / "Statistics/slides.pdf").write_bytes(b"tampered")
        (self.area / "Python/exercise.ipynb").unlink()
        self.make_file("Study/Semester 1/stray.txt")

        problems = lifecycle.verify(self.area)

        self.assertEqual(problems, {
            "changed": ["Statistics/slides.pdf"],
            "missing": ["Python/exercise.ipynb"],
            "extra": ["stray.txt"],
        })

    def test_verify_of_untouched_closed_area_is_clean(self):
        lifecycle.close(self.area)

        self.assertEqual(lifecycle.verify(self.area), {"changed": [], "missing": [], "extra": []})

    def test_undo_does_not_bypass_a_closed_collection(self):
        late = self.make_file("Downloads/late.pdf")
        fileops.move(late, self.area / "Statistics/late.pdf")
        lifecycle.close(self.area)

        skipped = undo.undo(last=2)

        self.assertTrue((self.area / "Statistics/late.pdf").exists())
        self.assertEqual([e.action for e in skipped], ["move"])
        self.assertEqual(lifecycle.verify(self.area), {"changed": [], "missing": [], "extra": []})

    def test_cannot_close_twice_or_reopen_open_area(self):
        with self.assertRaises(fileops.FilingError):
            lifecycle.reopen(self.area)
        lifecycle.close(self.area)
        with self.assertRaises(fileops.FilingError):
            lifecycle.close(self.area)


if __name__ == "__main__":
    unittest.main()
