import unittest

from aichivist import storage
from helpers import SandboxTest

HEADER = "| Place | Kind | Where | Holds | Price | Per |\n|---|---|---|---|---|---|\n"


class StorageTest(SandboxTest):
    def table(self, rows):
        return self.make_file("storage.md", (HEADER + rows).encode())

    def verdict(self, report, area):
        return next(v for v in report.areas if v.area == area)

    def test_example_documents_are_safe_photos_are_at_risk(self):
        report = storage.check(self.make_file("storage.md", storage.EXAMPLE.encode()))

        self.assertEqual(self.verdict(report, "Documents").advice, [])
        photos = self.verdict(report, "Photos")
        self.assertEqual((photos.copies, photos.away), (2, 0))
        self.assertTrue(any("away from home" in a for a in photos.advice))

    def test_backup_of_a_place_counts_its_areas(self):
        report = storage.check(self.table("| Laptop | computer | home | Study | 0 | |\n"
                                          "| Drive | drive | away | Backup of Laptop | 100 | once |\n"))

        self.assertEqual(self.verdict(report, "Study").places, ["Laptop", "Drive"])

    def test_only_in_the_cloud_is_a_risk(self):
        report = storage.check(self.table("| Cloud | cloud | away | Scans | 10 | year |\n"))

        self.assertTrue(any("only in the cloud" in a for a in self.verdict(report, "Scans").advice))

    def test_costs_per_year_from_month_year_and_once(self):
        report = storage.check(self.table("| A | cloud | away | X | 2,50 | month |\n"
                                          "| B | drive | home | X | CHF 100.- | once |\n"
                                          "| C | nas | home | X | 50 | year |\n"), lifetime=4)

        self.assertEqual(report.cost_per_year, {"A": 30.0, "B": 25.0, "C": 50.0})

    def test_unclear_price_or_kind_is_reported_not_guessed(self):
        report = storage.check(self.table("| Stick | usb | home | X | 20 | |\n"))

        self.assertEqual(len(report.problems), 2)
        self.assertEqual(report.cost_per_year, {})


if __name__ == "__main__":
    unittest.main()
