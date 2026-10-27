import unittest

from aichivist import catalog, describe, fileops, similar, style
from helpers import SandboxTest

POLICY = ("Example Health AG Policy basic insurance valid from 01.01.2026 for Alex Sample. The premium is CHF 320 per "
          "month and covers hospital, doctor visits and medication within Switzerland according to the general "
          "terms and conditions of the insurance. Deductible CHF 300. Insurance number 12345.")


class SimilarTest(SandboxTest):
    def test_new_scan_of_the_same_document_is_found_byte_checks_miss_it(self):
        self.make_file("archive/policy.txt", POLICY.encode())
        self.make_file("Downloads/policy scan.txt", (POLICY.replace("CHF 320", "CHF 320.-") + " Page 1").encode())

        hits = similar.find([self.root / "Downloads"], self.root / "archive")

        self.assertEqual(len(hits), 1)
        self.assertGreaterEqual(hits[0].similarity, 0.8)

    def test_different_documents_are_not_similar(self):
        self.make_file("archive/policy.txt", POLICY.encode())
        self.make_file("Downloads/other.txt", (" ".join(f"word{i}" for i in range(80))).encode())

        self.assertEqual(similar.find([self.root / "Downloads"], self.root / "archive"), [])

    def test_short_texts_are_never_flagged(self):
        self.make_file("Downloads/a.txt", b"short note")
        self.make_file("Downloads/b.txt", b"short note")

        self.assertEqual(similar.find([self.root / "Downloads"]), [])


class DescribeTest(SandboxTest):
    def test_suggests_date_issuer_kind_and_name(self):
        f = self.make_file("Downloads/scan_0042.txt", POLICY.encode())

        s = describe.suggest(f)

        self.assertEqual(s["date"], "2026-01-01")
        self.assertEqual(s["issuer"], "Example Health AG")
        self.assertEqual(s["kind"], "Policy")
        self.assertTrue(s["suggested_name"].startswith("2026-01-01 Example Health AG Policy"))
        self.assertTrue(s["suggested_name"].endswith(".txt"))

    def test_written_out_dates_are_understood(self):
        self.assertEqual(describe.find_date("Basel, 5. Juni 2026 – Erneuerung"), "2026-06-05")
        self.assertEqual(describe.find_date("Dated 9 September 2025"), "2025-09-09")

    def test_birth_dates_and_street_names_are_not_used(self):
        text = ("Muster Versicherung AG Police Hausrat. Versicherte Person: Alex Sample, geboren am 17.04.1998, "
                "Beispielstrasse 5, 4053 Basel. Gültig ab 01.03.2026 für die Wohnung und den Hausrat der Familie.")

        s = describe.suggest(self.make_file("x.txt", text.encode()), text)

        self.assertEqual(s["date"], "2026-03-01")
        self.assertNotIn("Beispielstrasse", s["suggested_name"])
        self.assertNotIn("Basel", s["suggested_name"])

    def test_subject_is_the_phrase_after_the_kind_word(self):
        text = "Example Health Ltd · Policy basic insurance · valid from 2026-01-01"

        self.assertEqual(describe.suggest(self.make_file("x.txt"), text)["suggested_name"],
                         "2026-01-01 Example Health Ltd Policy basic insurance.txt")

    def test_issuer_is_never_half_a_sentence(self):
        text = ("Sehr geehrte Frau Muster, Ihre Rechnung für das Abo Mobile vom 2. März 2026. Die Galaxus AG dankt "
                "Ihnen für Ihren Einkauf und wünscht Ihnen viel Freude mit dem neuen Abo.")

        s = describe.suggest(self.make_file("x.txt"), text)

        self.assertEqual(s["issuer"], "Galaxus AG")
        self.assertIn("Rechnung Abo Mobile", s["suggested_name"])

    def test_without_issuer_and_kind_the_current_name_is_kept(self):
        text = "Kalenderwoche 37 38 39 40 41 42 Montag Samstag Jahr 2025 Frühlingssemester ab 24.02.2025"
        f = self.make_file("Downloads/Hochschule Jahresstruktur 2025.pdf")

        s = describe.suggest(f, text)

        self.assertEqual(s["suggested_name"], "Hochschule Jahresstruktur 2025.pdf")
        self.assertFalse(s["confident"])

    def test_document_without_text_keeps_its_name(self):
        f = self.make_file("Downloads/photo.bin", b"\x00\x01")

        self.assertEqual(describe.suggest(f)["suggested_name"], "photo.bin")

    def test_catalog_prefill_writes_marked_rows_that_describe_can_replace(self):
        self.make_file("Area/_catalog.md", b"| File | Content | Search terms | Date |\n|---|---|---|---|\n")
        self.make_file("Area/policy.txt", POLICY.encode())

        catalog.add_missing(self.root / "Area/_catalog.md", prefill=True)
        text = (self.root / "Area/_catalog.md").read_text(encoding="utf-8")
        catalog.describe(self.root / "Area/_catalog.md", "policy.txt", "health policy", "health", "2026-01-01")

        self.assertIn("| policy.txt | ◇ Example Health AG Policy basic insurance", text)
        self.assertIn("| 2026-01-01 |", text)
        self.assertIn("| policy.txt | health policy |", (self.root / "Area/_catalog.md").read_text(encoding="utf-8"))


class StyleTest(SandboxTest):
    def test_examples_show_past_renames_and_names_per_folder(self):
        (self.root / "archive/Insurance").mkdir(parents=True)
        self.make_file("archive/Insurance/2025-01-01 Example Health Policy.pdf")
        src = self.make_file("Downloads/scan.pdf")
        fileops.move(src, self.root / "archive/Insurance/2026-01-01 Example Health Policy.pdf")

        ex = style.examples(self.root / "archive")

        self.assertEqual(ex["recent_renames"][0]["before"], "scan.pdf")
        self.assertEqual(len(ex["names_per_folder"]["Insurance"]), 2)


if __name__ == "__main__":
    unittest.main()
