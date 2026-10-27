import unittest

from aichivist import plan, structure
from helpers import SandboxTest


class StructureTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.area = self.root / "Documents"
        self.make_file("Documents/Finance/Invoices/2026/a.pdf")
        self.make_file("Documents/Finance/Invoices/2026/b.pdf")
        self.make_file("Documents/Finance/Invoices/2026/c.pdf")
        self.make_file("Documents/Car/Old/Older/Oldest/Deep/x.pdf")
        self.make_file("Documents/Car/Old/Older/Oldest/Deep/y.pdf")
        self.make_file("Documents/Car/Old/Older/Oldest/Deep/z.pdf")
        self.make_file("Documents/Travel/ticket.pdf")
        self.make_file("Documents/PDFs/scan1.pdf")
        self.make_file("Documents/PDFs/scan2.pdf")
        self.make_file("Documents/PDFs/scan3.pdf")
        self.make_file("Documents/Home/Rechnungen/r1.pdf")
        self.make_file("Documents/Home/Rechnungen/r2.pdf")
        self.make_file("Documents/Home/Rechnungen/r3.pdf")
        self.make_file("Documents/Finance/Rechnungen/r4.pdf")
        self.make_file("Documents/Finance/Rechnungen/r5.pdf")
        self.make_file("Documents/Finance/Rechnungen/r6.pdf")
        (self.area / "Neuer Ordner").mkdir()

    def kinds(self, report, kind):
        return [f.folder for f in report.findings if f.kind == kind]

    def test_finds_typical_structure_problems(self):
        report = structure.analyse(self.area)

        self.assertIn("Car/Old/Older/Oldest/Deep", self.kinds(report, "too_deep"))
        self.assertIn("Travel", self.kinds(report, "almost_empty"))
        self.assertIn("Neuer Ordner", self.kinds(report, "empty"))
        self.assertIn("Car/Old", self.kinds(report, "single_child"))
        self.assertIn("PDFs", self.kinds(report, "by_type"))
        self.assertIn("Rechnungen", self.kinds(report, "same_name"))

    def test_too_many_top_level_folders(self):
        for i in range(12):
            self.make_file(f"Documents/Area {i}/a.pdf")
            self.make_file(f"Documents/Area {i}/b.pdf")
            self.make_file(f"Documents/Area {i}/c.pdf")

        self.assertTrue(self.kinds(structure.analyse(self.area), "too_many_top"))

    def test_simple_fixes_become_plan_proposals_nothing_moves(self):
        plan_file = self.root / "plan.md"

        rows = structure.propose(self.area, plan_file)

        sources = {r.source for r in rows}
        self.assertIn(str(self.area / "Travel/ticket.pdf"), sources)          # almost empty → into the parent
        self.assertTrue((self.area / "Travel/ticket.pdf").exists())
        self.assertEqual({r.mark for r in rows}, {"?"})
        self.assertEqual(plan.check(plan_file)[0][1], None)

    def test_plain_language_report(self):
        text = "\n".join(structure.render(structure.analyse(self.area)))

        self.assertIn("folders deep", text)
        self.assertIn("sorted by file type", text)


if __name__ == "__main__":
    unittest.main()
