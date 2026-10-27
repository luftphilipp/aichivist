import hashlib
import unittest

from aichivist import bagit, fileops, lifecycle
from helpers import SandboxTest


class BagExportTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.area = self.root / "Study/Term 1"
        self.make_file("Study/Term 1/Statistics/slides.pdf", b"slides")
        self.make_file("Study/Term 1/100% done.txt", b"percent")
        lifecycle.close(self.area, note="all grades received")
        self.bag = self.root / "drive/Term 1 bag"

    def test_export_writes_bagit_structure(self):
        bagit.export(self.area, self.bag)

        self.assertEqual((self.bag / "bagit.txt").read_text(encoding="utf-8"),
                         "BagIt-Version: 1.0\nTag-File-Character-Encoding: UTF-8\n")
        self.assertEqual((self.bag / "data/Statistics/slides.pdf").read_bytes(), b"slides")
        manifest = (self.bag / "manifest-sha256.txt").read_text(encoding="utf-8")
        self.assertIn(f"{hashlib.sha256(b'slides').hexdigest()}  data/Statistics/slides.pdf", manifest)
        self.assertIn("  data/100% done.txt\n", manifest)  # like bagit-python: only CR/LF are encoded
        info = (self.bag / "bag-info.txt").read_text(encoding="utf-8")
        self.assertIn("Payload-Oxum: 13.2", info)
        self.assertIn("External-Description: all grades received", info)
        self.assertTrue((self.bag / "tagmanifest-sha256.txt").exists())

    def test_exported_bag_validates(self):
        bagit.export(self.area, self.bag)

        self.assertEqual(bagit.validate(self.bag), [])

    def test_validate_detects_changed_missing_and_extra_payload(self):
        bagit.export(self.area, self.bag)
        (self.bag / "data/Statistics/slides.pdf").write_bytes(b"tampered")
        (self.bag / "data/100% done.txt").unlink()
        (self.bag / "data/stray.txt").write_bytes(b"x")

        problems = bagit.validate(self.bag)

        self.assertIn("changed: data/Statistics/slides.pdf", problems)
        self.assertIn("missing: data/100% done.txt", problems)
        self.assertIn("not in manifest: data/stray.txt", problems)

    def test_only_closed_collections_are_exported(self):
        (self.root / "Open").mkdir()

        with self.assertRaises(fileops.FilingError):
            bagit.export(self.root / "Open", self.root / "drive/open bag")

    def test_existing_target_is_never_overwritten(self):
        self.make_file("drive/Term 1 bag/keep.txt")

        with self.assertRaises(fileops.FilingError):
            bagit.export(self.area, self.bag)


if __name__ == "__main__":
    unittest.main()
