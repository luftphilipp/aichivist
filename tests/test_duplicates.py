import unittest

from aichivist import duplicates
from helpers import SandboxTest


class DuplicatesTest(SandboxTest):
    def test_finds_identical_file_in_target_area(self):
        self.make_file("archive/Phone/2026-03-02 Example Mobile invoice.pdf", b"invoice bytes")
        new = self.make_file("Downloads/invoice(1).pdf", b"invoice bytes")

        found = duplicates.find([new], self.root / "archive")

        self.assertEqual([(m.source.name, m.match.name) for m in found],
                         [("invoice(1).pdf", "2026-03-02 Example Mobile invoice.pdf")])

    def test_finds_duplicates_within_the_inbox_itself(self):
        self.make_file("Downloads/invoice.pdf", b"same")
        self.make_file("Downloads/invoice copy.pdf", b"same")
        (self.root / "archive").mkdir()

        found = duplicates.find([self.root / "Downloads"], self.root / "archive")

        self.assertEqual([(m.source.name, m.match.name) for m in found], [("invoice copy.pdf", "invoice.pdf")])

    def test_keeps_the_name_without_copy_marker(self):
        self.make_file("Downloads/Scan (1).pdf", b"same")
        self.make_file("Downloads/Kopie von Scan.pdf", b"same")
        self.make_file("Downloads/Scan.pdf", b"same")
        (self.root / "archive").mkdir()

        found = duplicates.find([self.root / "Downloads"], self.root / "archive")

        self.assertEqual({m.match.name for m in found}, {"Scan.pdf"})
        self.assertEqual(len(found), 2)

    def test_large_files_differing_only_in_the_middle_are_no_duplicates(self):
        from aichivist.checksums import QUICK_BYTES
        size = QUICK_BYTES * 3
        self.make_file("archive/a.bin", b"A" * size)
        new = self.make_file("Downloads/b.bin", b"A" * (size // 2) + b"B" + b"A" * (size - size // 2 - 1))

        self.assertEqual(duplicates.find([new], self.root / "archive"), [])

    def test_same_size_but_different_content_is_no_duplicate(self):
        self.make_file("archive/a.pdf", b"AAAA")
        new = self.make_file("Downloads/b.pdf", b"BBBB")

        self.assertEqual(duplicates.find([new], self.root / "archive"), [])


if __name__ == "__main__":
    unittest.main()
