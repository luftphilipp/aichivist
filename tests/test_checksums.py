import hashlib
import unittest

from aichivist import checksums
from helpers import SandboxTest


class ChecksumTest(SandboxTest):
    def test_digest_is_sha256(self):
        f = self.make_file("a.pdf", b"record")

        self.assertEqual(checksums.digest(f), hashlib.sha256(b"record").hexdigest())

    def test_quick_digest_only_reads_head_and_tail(self):
        size = checksums.QUICK_BYTES * 3
        a = self.make_file("a.bin", b"A" * size)
        b = self.make_file("b.bin", b"A" * (size // 2) + b"B" + b"A" * (size - size // 2 - 1))

        self.assertEqual(checksums.quick_digest(a), checksums.quick_digest(b))
        self.assertNotEqual(checksums.digest(a), checksums.digest(b))

    def test_manifest_skips_aichivist_folders_and_system_files(self):
        self.make_file("area/doc.pdf")
        self.make_file("area/.aichivist-fulltext/doc.pdf.txt")
        self.make_file("area/.DS_Store")

        self.assertEqual(list(checksums.manifest(self.root / "area")), ["doc.pdf"])


if __name__ == "__main__":
    unittest.main()
