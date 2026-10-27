import subprocess
import unittest
from pathlib import Path
from unittest import mock

from aichivist import fileops, fulltext, inventory, rules
from helpers import SandboxTest

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "RULES.md"


class CheckRulesTest(SandboxTest):
    def test_unfilled_template_reports_placeholders(self):
        result = rules.check(TEMPLATE)

        self.assertGreater(len(result.placeholders), 5)
        self.assertFalse(result.ok)

    def test_filled_rules_report_missing_folders_only(self):
        (self.root / "Personal").mkdir()
        text = ("# Rules\n<!-- a <comment> is ignored -->\n| What | Where |\n|---|---|\n"
                f"| papers | `{self.root}/Personal/<Subject>/` |\n"
                f"| photos | `{self.root}/Photos/<Year>/` |\n")
        f = self.make_file("rules.md", text.encode("utf-8"))

        result = rules.check(f)

        self.assertEqual(result.placeholders, [])
        self.assertEqual(result.missing_folders, [f"{self.root}/Photos"])


    def test_command_variables_choices_and_named_base_folders_are_not_alarms(self):
        (self.root / "Cloud/Personal").mkdir(parents=True)
        text = (f"Cloud = `{self.root}/Cloud/`\n| What | Where |\n|---|---|\n"
                "| papers | Cloud `Personal/<Subject>/` |\n| photos | drive `<Alex|Sam>/Photos/<Year>/` |\n"
                "1. `aichivist inventory <inbox>` → what is new\n")
        f = self.make_file("rules.md", text.encode("utf-8"))

        result = rules.check(f)

        self.assertEqual((result.placeholders, result.missing_folders), ([], []))

    def test_a_span_that_starts_with_a_placeholder_is_still_unfilled(self):
        f = self.make_file("rules.md", b"Rules file: `<path to your RULES.md>`\n")

        self.assertEqual(rules.check(f).placeholders, [(1, "<path to your RULES.md>")])


class ManualMoveTest(SandboxTest):
    def test_moves_not_in_the_journal_are_reported_as_by_hand(self):
        inbox = self.root / "area"
        self.make_file("area/a.pdf", b"aaa")
        self.make_file("area/b.pdf", b"bbb")
        (inbox / "sub").mkdir()
        inventory.diff(inbox, save=True)
        fileops.move(inbox / "a.pdf", inbox / "sub/a.pdf")   # through aichivist
        (inbox / "b.pdf").rename(inbox / "sub/b.pdf")        # by hand (a human correction)

        changes = inventory.diff(inbox)

        self.assertEqual(inventory.manual_moves(inbox, changes), [("b.pdf", "sub/b.pdf")])


class OcrMyPdfTest(SandboxTest):
    def test_scanned_pdf_uses_ocrmypdf_sidecar_when_available(self):
        pdf = self.make_file("scan.pdf", b"%PDF")

        def fake_run(cmd, **kwargs):
            sidecar = Path(cmd[cmd.index("--sidecar") + 1])
            sidecar.write_text("first page text\fsecond page text", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with mock.patch.object(fulltext, "_pdf_text_layer", return_value=["", ""]), \
                mock.patch.object(fulltext.ocr, "recognize", return_value=None), \
                mock.patch.object(fulltext.shutil, "which", return_value="/usr/bin/ocrmypdf"), \
                mock.patch.object(fulltext.subprocess, "run", side_effect=fake_run):
            text, method = fulltext.extract(pdf)

        self.assertEqual(method, "pdf+ocr")
        self.assertIn("=== Page 2 ===\nsecond page text", text)
        self.assertEqual(pdf.read_bytes(), b"%PDF")  # original untouched

    def test_scanned_pdf_without_ocrmypdf_says_what_is_missing(self):
        pdf = self.make_file("scan.pdf", b"%PDF")

        with mock.patch.object(fulltext, "_pdf_text_layer", return_value=[""]), \
                mock.patch.object(fulltext.ocr, "recognize", return_value=None), \
                mock.patch.object(fulltext.shutil, "which", return_value=None):
            text, method = fulltext.extract(pdf)

        self.assertEqual(text, "=== Page 1 ===\n")
        self.assertIn("ocrmypdf", method)

    def test_built_in_ocr_is_preferred_for_scans(self):
        pdf = self.make_file("scan.pdf", b"%PDF")

        with mock.patch.object(fulltext, "_pdf_text_layer", return_value=[""]), \
                mock.patch.object(fulltext.ocr, "recognize", return_value=["page one", "page two"]):
            text, method = fulltext.extract(pdf)

        self.assertEqual(method, "pdf+ocr (built-in)")
        self.assertIn("=== Page 2 ===\npage two", text)


class BuiltInOcrTest(SandboxTest):
    def test_recognizes_text_with_the_system_engine(self):
        from aichivist import ocr
        if ocr.engine() is None:
            self.skipTest("no built-in OCR engine on this system")
        image = Path(__file__).resolve().parent.parent / "docs" / "social-preview.png"

        pages = ocr.recognize(image)

        if pages is None and ocr.engine() == "windows-ocr":
            self.skipTest("Windows OCR has no recognition language installed on this machine")
        self.assertIn("archivist", " ".join(pages or []).lower())


if __name__ == "__main__":
    unittest.main()
