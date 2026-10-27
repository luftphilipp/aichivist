import json
import os
import subprocess
import time
import unittest
from pathlib import Path
from unittest import mock

from aichivist import drives, survey
from helpers import SandboxTest

YEAR = 365 * 24 * 3600


class SurveyTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.place = self.root / "Downloads"
        self.make_file("Downloads/Unknown.pdf", b"statement")
        self.make_file("Downloads/scan_0042.pdf", b"policy")
        self.make_file("Downloads/invoice (1).pdf", b"invoice")
        self.make_file("Downloads/invoice.pdf", b"invoice")
        self.make_file("Downloads/2026-01-01 Example Health policy.pdf", b"named well")
        self.make_file("Downloads/photos/IMG_0001.jpg", b"jpeg" * 100)
        old = self.make_file("Downloads/old/report 2019.docx", b"old")
        stamp = time.time() - 4 * YEAR
        os.utime(old, (stamp, stamp))
        for i in range(30):
            self.make_file(f"Downloads/project/node_modules/pkg{i}/index.js", b"x")

    def survey(self, **kw):
        with mock.patch.object(drives, "health", return_value=drives.UNKNOWN):
            return survey.run([self.place], **kw)

    def test_counts_files_size_and_types(self):
        loc = self.survey().locations[0]

        self.assertEqual(loc.files, 7)
        self.assertEqual(loc.types[0].extension, ".pdf")
        self.assertEqual(loc.types[0].files, 5)

    def test_finds_duplicates_and_wasted_space(self):
        report = self.survey()

        self.assertEqual(len(report.duplicate_groups), 1)
        self.assertEqual(report.duplicate_waste, len(b"invoice"))

    def test_flags_unclear_document_names_only(self):
        names = sorted(Path(p).name for p in self.survey().locations[0].unclear)

        self.assertEqual(names, ["Unknown.pdf", "invoice (1).pdf", "scan_0042.pdf"])  # photos are not flagged

    def test_reports_stale_files(self):
        loc = self.survey(stale_years=3).locations[0]

        self.assertEqual([Path(p).name for p in loc.stale], ["report 2019.docx"])

    def test_flags_folders_unsuitable_for_cloud_sync(self):
        loc = self.survey().locations[0]

        self.assertEqual([(h.folder, h.files) for h in loc.heavy], [("project/node_modules", 30)])

    def test_program_folders_are_reported_and_not_inspected(self):
        self.make_file("Downloads/Example Game/steamapps/save.dat", b"game")

        loc = self.survey().locations[0]

        self.assertEqual(loc.programs, [("Example Game", "Steam library")])
        self.assertEqual(loc.files, 7)  # the game's files are not counted as documents
        self.assertIn("program folder", "\n".join(survey.render(self.survey())))

    def test_project_and_data_folders_are_one_unit_and_not_hashed(self):
        self.make_file("Downloads/thesis-code/.git/HEAD", b"ref")
        self.make_file("Downloads/thesis-code/train.py", b"same")
        self.make_file("Downloads/thesis-code/copy.py", b"same")

        report = self.survey()

        loc = report.locations[0]
        self.assertIn(("thesis-code", 3), [(h.folder, h.files) for h in loc.heavy])
        self.assertEqual(len(report.duplicate_groups), 1)  # only the invoice pair, nothing inside the project

    def test_cloud_only_files_are_counted_but_never_read(self):
        with mock.patch.object(survey, "is_cloud_only", side_effect=lambda p, st: p.name == "Unknown.pdf"), \
                mock.patch.object(survey, "digest", side_effect=AssertionError("must not read")):
            loc = self.survey(find_duplicates=False).locations[0]

        self.assertEqual(loc.cloud_only, 1)

    def test_json_friendly_and_human_report(self):
        report = self.survey()

        json.dumps(survey.as_dict(report))
        text = "\n".join(survey.render(report))
        self.assertIn("duplicate", text)
        self.assertIn("unclear names", text)


class DriveHealthTest(unittest.TestCase):
    def test_without_smartctl_health_is_unknown_with_hint(self):
        with mock.patch.object(drives.shutil, "which", return_value=None), \
                mock.patch.object(drives, "_diskutil_status", return_value=None):
            info = drives.health(Path("/"))

        self.assertEqual(info.status, "unknown")
        self.assertIn("smartmontools", info.detail)

    def test_parses_smartctl_json(self):
        data = {"smart_status": {"passed": True}, "power_on_time": {"hours": 4430}, "temperature": {"current": 49}}
        done = subprocess.CompletedProcess([], 0, json.dumps(data), "")
        with mock.patch.object(drives.shutil, "which", return_value="/usr/sbin/smartctl"), \
                mock.patch.object(drives, "device_for", return_value="/dev/sda"), \
                mock.patch.object(drives.subprocess, "run", return_value=done):
            info = drives.health(Path("/"))

        self.assertEqual((info.status, info.power_on_hours, info.temperature), ("passed", 4430, 49))

    def test_failed_drive_is_reported_as_failed(self):
        data = {"smart_status": {"passed": False}}
        done = subprocess.CompletedProcess([], 8, json.dumps(data), "")
        with mock.patch.object(drives.shutil, "which", return_value="/usr/sbin/smartctl"), \
                mock.patch.object(drives, "device_for", return_value="/dev/sda"), \
                mock.patch.object(drives.subprocess, "run", return_value=done):
            self.assertEqual(drives.health(Path("/")).status, "failed")

    def test_whole_disk_from_partition(self):
        self.assertEqual(drives.whole_disk("/dev/disk4s2"), "/dev/disk4")
        self.assertEqual(drives.whole_disk("/dev/sda1"), "/dev/sda")
        self.assertEqual(drives.whole_disk("/dev/nvme0n1p2"), "/dev/nvme0n1")


if __name__ == "__main__":
    unittest.main()
