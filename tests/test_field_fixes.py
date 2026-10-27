"""Fixes from a field report: large filing runs, partly onto an exFAT drive."""
import errno
import os
import unittest
from pathlib import Path
from unittest import mock

from test_commands import run

from aichivist import apps, catalog, cli, config, fileops, plan, undo
from aichivist.fileops import FilingError
from helpers import SandboxTest

CAN_LINK = hasattr(os, "symlink") and os.name != "nt"
HAS_UID = hasattr(os, "getuid")
POSIX_NAMES = os.name != "nt"  # Windows allows neither "|" nor spaces at the end of file names
EXDEV = OSError(errno.EXDEV, "cross-device link")


class DriveTest(SandboxTest):
    def test_copy_to_a_drive_without_file_flags_keeps_content_and_dates(self):
        folder = self.root / "inbox/photos"
        photo = self.make_file("inbox/photos/sub/a.jpg", b"x" * 500)
        os.utime(photo, (1_600_000_000, 1_600_000_000))
        dst = self.root / "drive/photos"
        dst.parent.mkdir()
        refused = OSError(errno.EINVAL, "Invalid argument")

        with mock.patch("aichivist.fileops.os.rename", side_effect=EXDEV), \
                mock.patch("shutil.copystat", side_effect=refused):
            fileops.move(folder, dst)

        self.assertFalse(folder.exists())
        self.assertEqual((dst / "sub/a.jpg").read_bytes(), b"x" * 500)
        self.assertEqual(int((dst / "sub/a.jpg").stat().st_mtime), 1_600_000_000)

    def test_other_copy_errors_still_stop_and_keep_the_original(self):
        src = self.make_file("inbox/a.pdf")
        (self.root / "drive").mkdir()

        with mock.patch("aichivist.fileops.os.rename", side_effect=EXDEV), \
                mock.patch("shutil.copystat", side_effect=OSError(errno.EIO, "I/O error")), \
                self.assertRaises(OSError):
            fileops.move(src, self.root / "drive/a.pdf")

        self.assertTrue(src.exists())
        self.assertFalse((self.root / "drive/a.pdf").exists())


@unittest.skipUnless(CAN_LINK, "symlinks")
class BrokenLinkTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.link = self.root / "home/Relocated Items.nosync"
        self.link.parent.mkdir()
        os.symlink(self.root / "nowhere", self.link)

    def test_broken_link_goes_to_the_trash_and_comes_back(self):
        target = fileops.trash(self.link, ctx=apps.Context([], {}))

        self.assertTrue(target.is_symlink())
        self.assertFalse(self.link.is_symlink())
        undo.undo(last=1)
        self.assertTrue(self.link.is_symlink())

    def test_link_moves_between_drives_as_a_link(self):
        (self.root / "drive").mkdir()
        dst = self.root / "drive/Relocated Items.nosync"

        with mock.patch("aichivist.fileops.os.rename", side_effect=EXDEV):
            fileops.move(self.link, dst, ctx=apps.Context([], {}))

        self.assertEqual(os.readlink(dst), str(self.root / "nowhere"))
        self.assertFalse(self.link.is_symlink())

    def test_a_broken_link_at_the_target_is_never_overwritten(self):
        src = self.make_file("inbox/a.pdf")

        with self.assertRaises(FilingError):
            fileops.move(src, self.link)

        self.assertTrue(self.link.is_symlink())


@unittest.skipUnless(HAS_UID, "volume trash folders are a macOS/Linux concept")
class VolumeTrashTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.drive = self.root / "Volumes/WD"
        self.drive.mkdir(parents=True)
        os.environ.pop("AICHIVIST_TRASH")
        mounts = mock.patch("aichivist.config.mount_point",
                            side_effect=lambda p: self.drive if self.drive in Path(p).parents else Path("/"))
        drives = mock.patch("aichivist.config.same_drive",
                            side_effect=lambda a, b: (self.drive in Path(a).parents) == (self.drive in Path(b).parents))
        for patch in (mounts, drives):
            patch.start()
            self.addCleanup(patch.stop)

    def test_files_on_another_drive_go_to_that_drives_trash(self):
        dup = self.make_file("Volumes/WD/Fotos/dup.jpg")

        target = fileops.trash(dup, ctx=apps.Context([], {}))

        self.assertIn(self.drive, target.parents)
        undo.undo(last=1)
        self.assertTrue(dup.exists())

    def test_home_drive_keeps_the_home_trash(self):
        with mock.patch.dict("os.environ", {"HOME": str(self.root / "home"), "XDG_DATA_HOME": ""}):
            self.assertNotIn(self.drive, config.trash_dir(self.root / "home/a.pdf").parents)


    def test_real_drives_are_compared_by_device(self):
        mock.patch.stopall()
        self.assertTrue(config.same_drive(self.root, self.root / "missing/a.pdf"))


class ProgramCheckTest(SandboxTest):
    def ctx(self):
        return apps.Context([], {})

    def test_a_project_next_to_the_target_does_not_block_filing(self):
        self.make_file("Docs/proj/pyproject.toml")
        notes = self.make_file("Docs/proj notes/a.md").parent

        fileops.move(notes, self.root / "Docs/proj feedback", ctx=self.ctx())

        self.assertTrue((self.root / "Docs/proj feedback/a.md").exists())

    def test_filing_into_a_project_is_still_refused(self):
        self.make_file("Docs/proj/pyproject.toml")
        letter = self.make_file("inbox/letter.pdf")

        with self.assertRaises(FilingError):
            fileops.move(letter, self.root / "Docs/proj/letter.pdf", ctx=self.ctx())

    def test_unreadable_folder_inside_does_not_stop_the_check(self):
        library = self.root / "Big/Library"
        (library / ".obsidian").mkdir(parents=True)
        real_exists = Path.exists

        def exists(path, *args, **kwargs):
            if library in path.parents:
                raise PermissionError(errno.EACCES, "Permission denied", str(path))
            return real_exists(path, *args, **kwargs)

        with mock.patch.object(Path, "exists", exists):
            self.assertIsNone(apps._kind(library))

    def test_own_hidden_folders_in_documents_are_not_program_folders(self):
        home = self.root / "home"
        with mock.patch.object(Path, "home", return_value=home), \
                mock.patch("aichivist.apps.tempfile.gettempdir", return_value=str(self.root / "tmp")), \
                mock.patch("aichivist.apps.managed_places", return_value=[]):
            self.assertIsNone(apps.place_risk(home / "Documents/.filing/tools/progress.command"))
            risk = apps.place_risk(home / ".config/app/settings.json")

        self.assertIn(str(home / ".config"), risk)

    def test_trash_message_names_the_way_to_delete_anyway(self):
        vault = self.make_file("Notes/.obsidian/app.json").parent.parent

        with self.assertRaises(FilingError) as err:
            fileops.trash(vault, ctx=self.ctx())

        self.assertIn("--app-data", str(err.exception))
        self.assertNotIn("--leave-link", str(err.exception))


class PlanFixesTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.plan = self.root / "plan.md"
        (self.root / "out").mkdir()

    def test_folder_from_an_earlier_row_counts_as_present(self):
        firm = self.make_file("in/Company/a.pdf").parent
        letter = self.make_file("in/letter.pdf")
        plan.add(self.plan, firm, self.root / "out/Company", "folder")
        plan.add(self.plan, letter, self.root / "out/Company/letter.pdf", "into it")
        plan.approve(self.plan)

        self.assertEqual([p for _, p in plan.check(self.plan)], [None, None])
        self.assertEqual(plan.apply(self.plan).done, 2)

    @unittest.skipUnless(POSIX_NAMES, "Windows file names")
    def test_pipe_in_a_file_name_survives_the_plan(self):
        src = self.make_file("in/Offer | Example Ltd.pdf")
        plan.add(self.plan, src, self.root / "out/Offer | Example.pdf", "a | b")

        row = plan.read(self.plan)[0]

        expected = (str(src), str(self.root / "out/Offer | Example.pdf"), "a | b")
        self.assertEqual((row.source, row.target, row.reason), expected)
        plan.approve(self.plan)
        self.assertEqual(plan.apply(self.plan).done, 1)

    @unittest.skipUnless(POSIX_NAMES, "Windows file names")
    def test_spaces_at_the_end_of_a_name_are_kept(self):
        music = self.make_file("in/Music /a.mp3").parent
        plan.add(self.plan, music, self.root / "out/Music2", "trailing space")

        self.assertEqual(plan.read(self.plan)[0].source, str(music))
        self.assertEqual([p for _, p in plan.check(self.plan)], [None])

    def test_apply_names_each_failed_row(self):
        a = self.make_file("in/a.pdf")
        plan.add(self.plan, a, self.root / "missing/a.pdf", "no folder")
        plan.approve(self.plan)

        code, out = run("plan", "apply", str(self.plan))

        self.assertEqual(code, 1)
        self.assertIn(str(a), out)
        self.assertIn("error:", out)


class GermanCatalogTest(SandboxTest):
    def test_rows_to_describe_follow_the_catalog_language(self):
        area = self.root / "Personal"
        self.make_file("Personal/New.pdf")
        (area / "_Katalog.md").write_text("| Datei | Inhalt | Suchbegriffe | Datum |\n|---|---|---|---|\n",
                                          encoding="utf-8")

        catalog.add_missing(area / "_Katalog.md")

        text = (area / "_Katalog.md").read_text(encoding="utf-8")
        self.assertIn("## Zu beschreiben", text)
        self.assertIn("| New.pdf | ⚠ zu beschreiben |", text)
        self.assertNotIn("Search terms", text)
        catalog.describe(area / "_Katalog.md", "New.pdf", "Policy", "Insurance", "2026")
        self.assertIn("| New.pdf | Policy | Insurance | 2026 |", (area / "_Katalog.md").read_text("utf-8"))


class NoteHelpTest(SandboxTest):
    def test_help_names_the_actions_and_an_example(self):
        sub = next(a for a in cli.build_parser()._actions if a.dest == "command")
        out = sub.choices["note"].format_help()

        self.assertIn("aichivist note move", out)
        self.assertIn("rename", out)
