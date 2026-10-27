import unittest

from aichivist import catalog_page
from helpers import SandboxTest

CATALOG = ("# Catalog\n\n| File | Content | Search terms | Date |\n|---|---|---|---|\n"
           "| `Insurance/policy.pdf` | Health <policy> | health, insurance | 2026-01-01 |\n"
           "| gone.pdf | missing file | | |\n\n## To describe\n| File | Content | Search terms | Date |\n"
           "|---|---|---|---|\n| new.pdf | ⚠ to describe | | |\n")


class CatalogPageTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.area = self.root / "Personal"
        self.make_file("Personal/_catalog.md", CATALOG.encode())
        self.make_file("Personal/Insurance/policy.pdf")
        self.make_file("Personal/Car/_Katalog.md", b"| Datei | Inhalt |\n|---|---|\n| car.pdf | Fahrzeugausweis |\n")

    def test_all_catalogs_of_the_area_become_one_page(self):
        out = catalog_page.write(self.area)
        page = out.read_text(encoding="utf-8")

        self.assertTrue(str(out).startswith(str(self.home)))  # not written into the area
        self.assertIn("Health &lt;policy&gt;", page)            # content is escaped
        self.assertIn("Fahrzeugausweis", page)
        self.assertIn("new.pdf", page)
        self.assertIn("4 entries from 2 catalog(s)", page)

    def test_existing_files_are_linked_missing_ones_are_not(self):
        page = catalog_page.write(self.area).read_text(encoding="utf-8")

        self.assertIn((self.area / "Insurance/policy.pdf").as_uri(), page)
        self.assertNotIn("gone.pdf</a>", page)


if __name__ == "__main__":
    unittest.main()
