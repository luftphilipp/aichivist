import unittest

from aichivist import journal, lifecycle, plan
from helpers import SandboxTest


class PlanTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.plan = self.root / "plan.md"
        self.inbox = self.root / "Downloads"
        self.archive = self.root / "archive/Insurance"
        self.archive.mkdir(parents=True)

    def test_add_writes_proposed_rows_with_header(self):
        src = self.make_file("Downloads/scan.pdf")

        plan.add(self.plan, src, self.archive / "2026-01-01 Policy.pdf", "health policy")

        rows = plan.read(self.plan)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].mark, "?")
        self.assertEqual(rows[0].reason, "health policy")
        self.assertIn("| ✓ | Source | Target | Reason |", self.plan.read_text(encoding="utf-8"))

    def test_tilde_paths_mean_the_home_folder(self):
        from unittest import mock
        src = self.make_file("Downloads/scan.pdf")
        with mock.patch.dict("os.environ", {"HOME": str(self.root), "USERPROFILE": str(self.root)}):
            row = plan.add(self.plan, "~/Downloads/scan.pdf", "~/archive/Insurance/P.pdf", "tilde")

        self.assertEqual(row.source, str(src))
        self.assertEqual(row.target, str(self.archive / "P.pdf"))

    def test_check_reports_problems_per_row(self):
        ok = self.make_file("Downloads/a.pdf")
        taken = self.make_file("archive/Insurance/b.pdf")
        plan.add(self.plan, ok, self.archive / "A.pdf", "fine")
        plan.add(self.plan, self.inbox / "missing.pdf", self.archive / "M.pdf", "gone")
        plan.add(self.plan, self.make_file("Downloads/b.pdf"), taken, "would overwrite")
        plan.add(self.plan, self.make_file("Downloads/c.pdf"), self.root / "nowhere/C.pdf", "no folder")

        problems = [p for _, p in plan.check(self.plan)]

        self.assertIsNone(problems[0])
        self.assertIn("source missing", problems[1])
        self.assertIn("target exists", problems[2])
        self.assertIn("target folder missing", problems[3])

    def test_check_finds_two_rows_with_the_same_target(self):
        plan.add(self.plan, self.make_file("Downloads/a.pdf"), self.archive / "X.pdf", "one")
        plan.add(self.plan, self.make_file("Downloads/b.pdf"), self.archive / "X.pdf", "two")

        self.assertIn("same target", plan.check(self.plan)[1][1])

    def test_apply_executes_only_approved_rows_and_records_status(self):
        a = self.make_file("Downloads/a.pdf")
        b = self.make_file("Downloads/b.pdf")
        plan.add(self.plan, a, self.archive / "A.pdf", "approved")
        plan.add(self.plan, b, self.archive / "B.pdf", "not approved")
        plan.approve(self.plan, rows=[1])

        results = plan.apply(self.plan)

        self.assertTrue((self.archive / "A.pdf").exists())
        self.assertTrue(b.exists())
        self.assertEqual([r.mark for r in plan.read(self.plan)], ["done", "?"])
        self.assertEqual(results.done, 1)
        self.assertEqual(journal.read()[0].action, "apply_plan")

    def test_trash_rows_go_to_trash(self):
        dup = self.make_file("Downloads/copy.pdf")
        plan.add(self.plan, dup, plan.TRASH, "duplicate of archive/A.pdf")
        plan.approve(self.plan)

        plan.apply(self.plan)

        self.assertFalse(dup.exists())
        self.assertTrue((self.trash / "copy.pdf").exists())

    def test_failed_row_is_marked_and_others_continue(self):
        lifecycle.close(self.archive)
        a = self.make_file("Downloads/a.pdf")
        b = self.make_file("Downloads/b.pdf")
        (self.root / "other").mkdir()
        plan.add(self.plan, a, self.archive / "A.pdf", "into closed collection")
        plan.add(self.plan, b, self.root / "other/B.pdf", "fine")
        plan.approve(self.plan)

        results = plan.apply(self.plan)

        marks = [r.mark for r in plan.read(self.plan)]
        self.assertTrue(marks[0].startswith("error"))
        self.assertEqual(marks[1], "done")
        self.assertEqual((results.done, results.failed), (1, 1))

    def test_applying_twice_does_nothing_new(self):
        plan.add(self.plan, self.make_file("Downloads/a.pdf"), self.archive / "A.pdf", "once")
        plan.approve(self.plan)
        plan.apply(self.plan)

        self.assertEqual(plan.apply(self.plan).done, 0)


if __name__ == "__main__":
    unittest.main()
