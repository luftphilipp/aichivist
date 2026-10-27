import importlib.util
import unittest
import zipfile

from aichivist import fileops, fulltext, lifecycle
from helpers import SandboxTest

HAS_PYPDF = importlib.util.find_spec("pypdf") is not None


def make_docx(path, paragraphs):
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", f'<w:document xmlns:w="w"><w:body>{body}</w:body></w:document>')


class ExtractTest(SandboxTest):
    def test_plain_text_and_markdown(self):
        f = self.make_file("a/notes.md", b"# Statistics\nmedian and mode")

        text, method = fulltext.extract(f)

        self.assertIn("median", text)
        self.assertEqual(method, "text")

    def test_word_document(self):
        f = self.root / "lecture.docx"
        make_docx(f, ["Descriptive statistics", "Scale levels"])

        text, method = fulltext.extract(f)

        self.assertIn("Scale levels", text)
        self.assertEqual(method, "docx")

    def test_powerpoint_slides_in_numeric_order(self):
        f = self.root / "deck.pptx"
        with zipfile.ZipFile(f, "w") as z:
            for n, words in ((10, "tenth"), (2, "second")):
                z.writestr(f"ppt/slides/slide{n}.xml", f'<p:sld xmlns:a="a"><a:p><a:t>{words}</a:t></a:p></p:sld>')

        text, method = fulltext.extract(f)

        self.assertEqual(method, "pptx")
        self.assertLess(text.index("second"), text.index("tenth"))

    def test_unknown_type_is_reported_not_guessed(self):
        f = self.make_file("a/data.bin", b"\x00\x01")

        text, method = fulltext.extract(f)

        self.assertEqual(text, "")
        self.assertTrue(method.startswith("unsupported"))

    @unittest.skipUnless(HAS_PYPDF, "pypdf not installed")
    def test_pdf_without_text_layer_is_reported_as_scan(self):
        from pypdf import PdfWriter
        f = self.root / "scan.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        with open(f, "wb") as fh:
            writer.write(fh)

        text, method = fulltext.extract(f)

        self.assertIn("=== Page 1 ===", text)
        self.assertIn("no text layer", method)

    @unittest.skipUnless(HAS_PYPDF, "pypdf not installed")
    def test_damaged_pdf_is_reported_not_fatal(self):
        f = self.make_file("broken.pdf", b"%PDF-1.4 not really")

        text, method = fulltext.extract(f)

        self.assertEqual(text, "")
        self.assertTrue(method.startswith("error"))

    def test_damaged_office_file_is_reported_not_fatal(self):
        f = self.make_file("broken.docx", b"not a zip")

        self.assertTrue(fulltext.extract(f)[1].startswith("error"))


class ClosedCollectionIndexTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.area = self.root / "Study/Semester 1"
        self.make_file("Study/Semester 1/Statistics/summary.md", b"The median splits the data in half")
        make_docx(self.area / "Statistics/lecture.docx", ["Scale levels: nominal, ordinal"])

    def test_open_collection_has_no_index(self):
        self.assertFalse(fulltext.index_dir(self.area).exists())
        with self.assertRaises(fileops.FilingError):
            fulltext.search(self.area, "median")

    def test_closing_builds_index_and_search_finds_terms(self):
        lifecycle.close(self.area)

        hits = fulltext.search(self.area, "ordinal")

        self.assertEqual([h.file for h in hits], ["Statistics/lecture.docx"])
        self.assertIn("ordinal", hits[0].snippet)

    def test_search_matches_all_terms_case_insensitive(self):
        lifecycle.close(self.area)

        self.assertEqual(len(fulltext.search(self.area, "MEDIAN half")), 1)
        self.assertEqual(fulltext.search(self.area, "median ordinal"), [])

    def test_catalog_is_not_indexed(self):
        self.make_file("Study/Semester 1/_catalog.md", b"| summary.md | median |")
        lifecycle.close(self.area)

        self.assertEqual([h.file for h in fulltext.search(self.area, "median")], ["Statistics/summary.md"])

    def test_index_is_not_part_of_the_fixity_manifest(self):
        lifecycle.close(self.area)

        self.assertEqual(lifecycle.verify(self.area), {"changed": [], "missing": [], "extra": []})

    def test_reopen_drops_the_index(self):
        lifecycle.close(self.area)
        lifecycle.reopen(self.area, note="late grade")

        self.assertFalse(fulltext.index_dir(self.area).exists())


if __name__ == "__main__":
    unittest.main()
