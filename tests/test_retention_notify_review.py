import os
import time
import unittest
import urllib.request
from datetime import date
from pathlib import Path

from aichivist import notify, plan, retention, review
from helpers import SandboxTest

YEAR = 365.25 * 24 * 3600


class RetentionTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.area = self.root / "Finance"
        self.make_file("Finance/2012-03-01 Bank statement.pdf")
        self.make_file("Finance/2025-03-01 Bank statement.pdf")
        old = self.make_file("Finance/receipt.pdf")
        stamp = time.time() - 12 * YEAR
        os.utime(old, (stamp, stamp))

    def test_due_uses_the_date_in_the_name_or_the_file_date(self):
        names = [os.path.basename(d.path) for d in retention.due(self.area, 10, today=date(2026, 10, 23))]

        self.assertEqual(names, ["2012-03-01 Bank statement.pdf", "receipt.pdf"])

    def test_propose_offers_long_term_archive_and_never_acts_alone(self):
        plan_file = self.root / "plan.md"
        (self.root / "Long-term/Finance").mkdir(parents=True)

        rows = retention.propose(self.area, 10, plan_file, archive=self.root / "Long-term/Finance")

        self.assertEqual({r.mark for r in rows}, {"?"})
        expected = self.root / "Long-term" / "Finance" / "2012-03-01 Bank statement.pdf"
        self.assertEqual(Path(rows[0].target).resolve(), expected.resolve())  # works with \\ on Windows too
        self.assertIn("TRASH to delete", rows[0].reason)
        self.assertTrue((self.area / "2012-03-01 Bank statement.pdf").exists())

    def test_without_archive_the_choice_is_deletion_via_trash(self):
        rows = retention.propose(self.area, 10, self.root / "plan.md")

        self.assertEqual({r.target for r in rows}, {plan.TRASH})


class NotifyTest(SandboxTest):
    def test_message_only_from_the_threshold_on(self):
        for i in range(24):
            self.make_file(f"Downloads/f{i}.pdf")

        self.assertEqual(notify.message(notify.count([self.root / "Downloads"]), 25), "")
        self.make_file("Downloads/f24.pdf")
        self.assertIn("25 files waiting", notify.message(notify.count([self.root / "Downloads"]), 25))


class ReviewTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.plan = self.root / "plan.md"
        (self.root / "archive").mkdir()
        for name in ("a", "b", "c"):
            source = self.make_file(f"Downloads/{name}.pdf")
            plan.add(self.plan, source, self.root / f"archive/{name.upper()}.pdf", name)

    def test_page_lists_proposals_with_checkboxes_and_links(self):
        page = review.render(self.plan)

        self.assertEqual(page.count('type="checkbox"'), 3)
        self.assertIn("file://", page)
        self.assertIn("A.pdf", page)

    def test_only_ticked_rows_are_approved(self):
        review.approve_from_form(self.plan, "row=1&row=3")

        self.assertEqual([r.mark for r in plan.read(self.plan)], ["x", "?", "x"])

    def test_local_page_round_trip(self):
        url = review.serve(self.plan, open_browser=False, block=False)

        page = urllib.request.urlopen(url, timeout=5).read().decode()
        done = urllib.request.urlopen(url, data=b"row=2", timeout=5).read().decode()

        self.assertIn("3 proposals", page)
        self.assertIn("1 rows approved", done)
        self.assertEqual([r.mark for r in plan.read(self.plan)], ["?", "x", "?"])


if __name__ == "__main__":
    unittest.main()
