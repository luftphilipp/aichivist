import unittest

from aichivist import catalog
from helpers import SandboxTest

CATALOG = """# Catalog Personal

## Insurance
| File | Content | Search terms | Date |
|---|---|---|---|
| Insurance/2026-01-01 Example Health policy.pdf | basic insurance | health | 2026-01-01 |
| `Insurance/Example Offer.pdf` | offer | quote | – |

## Vehicles
| File | Content | Search terms | Date |
|---|---|---|---|
| Vehicles/Sale photos/ | 3 photos for the sale ad | photos | – |
| Vehicles/Gone.pdf | listed but deleted | – | – |
"""


class CatalogCheckTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.area = self.root / "Personal"
        self.make_file("Personal/_catalog.md", CATALOG.encode("utf-8"))
        self.make_file("Personal/Insurance/2026-01-01 Example Health policy.pdf")
        self.make_file("Personal/Insurance/Example Offer.pdf")
        self.make_file("Personal/Vehicles/Sale photos/IMG_1.jpg")
        self.make_file("Personal/Vehicles/Sale photos/IMG_2.jpg")

    def test_reports_files_missing_in_catalog_and_entries_without_file(self):
        self.make_file("Personal/Insurance/New policy.pdf")

        result = catalog.check(self.area / "_catalog.md")

        self.assertEqual(result.not_in_catalog, ["Insurance/New policy.pdf"])
        self.assertEqual(result.not_on_disk, ["Vehicles/Gone.pdf"])

    def test_folder_entries_cover_everything_inside(self):
        result = catalog.check(self.area / "_catalog.md")

        self.assertNotIn("Vehicles/Sale photos/IMG_1.jpg", result.not_in_catalog)

    def test_ignores_catalog_itself_hidden_and_system_files(self):
        self.make_file("Personal/.DS_Store")
        self.make_file("Personal/.aichivist-closed.json")
        self.make_file("Personal/Insurance/Thumbs.db")

        result = catalog.check(self.area / "_catalog.md")

        self.assertEqual(result.not_in_catalog, [])

    def test_add_missing_appends_rows_to_describe(self):
        self.make_file("Personal/Insurance/New policy.pdf")

        added = catalog.add_missing(self.area / "_catalog.md")

        self.assertEqual(added, ["Insurance/New policy.pdf"])
        text = (self.area / "_catalog.md").read_text(encoding="utf-8")
        self.assertIn("| Insurance/New policy.pdf | ⚠ to describe |", text)
        self.assertEqual(catalog.check(self.area / "_catalog.md").not_in_catalog, [])

    def test_clean_area_has_no_problems(self):
        clean = CATALOG.replace("| Vehicles/Gone.pdf | listed but deleted | – | – |\n", "")
        (self.area / "_catalog.md").write_text(clean, encoding="utf-8")

        self.assertTrue(catalog.check(self.area / "_catalog.md").ok)


class UmlautTest(SandboxTest):
    def test_umlauts_match_however_they_are_stored(self):
        import unicodedata
        decomposed = unicodedata.normalize("NFD", "Prüfungsplan.pdf")   # as macOS stores file names
        self.make_file("Area/" + decomposed)
        catalog_text = "| File | Content |\n|---|---|\n| Prüfungsplan.pdf | exam dates |\n"
        self.make_file("Area/_catalog.md", catalog_text.encode())

        self.assertTrue(catalog.check(self.root / "Area/_catalog.md").ok)


if __name__ == "__main__":
    unittest.main()
