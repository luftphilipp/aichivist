import os
import unittest
from unittest import mock

from aichivist import apps, fileops, plan, undo
from aichivist.fileops import FilingError
from helpers import SandboxTest

CAN_LINK = hasattr(os, "symlink") and os.name != "nt"


class ProgramDataTest(SandboxTest):
    def ctx(self, open_files=None):
        return apps.Context(apps.find_links([self.root]), open_files or {})

    def test_ordinary_document_is_safe_to_move(self):
        f = self.make_file("Downloads/letter.pdf")

        self.assertEqual(apps.risks(f, self.ctx()), [])

    def test_files_of_program_libraries_and_projects_are_recognised(self):
        photo = self.make_file("Pictures/Photos Library.photoslibrary/originals/a.heic")
        note = self.make_file("Notes/.obsidian/app.json").parent.parent / "idea.md"
        note.write_text("x")
        code = self.make_file("Code/tool/pyproject.toml").parent / "main.py"
        code.write_text("x")

        self.assertIn("Photos library", apps.risks(photo, self.ctx())[0])
        self.assertIn("Obsidian vault", apps.risks(note, self.ctx())[0])
        self.assertIn("code project", apps.risks(code, self.ctx())[0])
        self.assertIn("contains a code project", apps.risks(self.root / "Code", self.ctx())[0])

    @unittest.skipUnless(CAN_LINK, "symlinks")
    def test_a_link_pointing_to_the_folder_is_found(self):
        game = self.make_file("Programs/Game/save.dat").parent
        os.symlink(game, self.root / "Game shortcut")

        self.assertIn("Game shortcut", " ".join(apps.risks(game, self.ctx())))

    def test_windows_shortcut_pointing_to_the_file_is_found(self):
        f = self.make_file("Programs/Tool/config.ini")
        self.make_file("Desktop/Tool.lnk", b"\x4c\x00\x00\x00" + str(f).encode("utf-16-le") + b"\x00\x00")

        self.assertIn("Tool.lnk", " ".join(apps.risks(f, self.ctx())))

    def test_open_file_names_the_program(self):
        f = self.make_file("db.sqlite")

        found = apps.risks(f, self.ctx({os.path.realpath(f): "Banking"}))

        self.assertIn("open in Banking", found[0])

    def test_program_folders_are_recognised_but_cloud_folders_are_not(self):
        library = self.make_file("Library/Application Support/App/settings.json")
        cloud = self.make_file("Library/Mobile Documents/com~apple~CloudDocs/Personal/tax.pdf")
        hidden = self.make_file(".steam/game/data.bin")
        with mock.patch.object(apps.Path, "home", return_value=self.root), \
                mock.patch.object(apps, "managed_places", return_value=[self.root / "Library"]), \
                mock.patch.object(apps.tempfile, "gettempdir", return_value=str(self.root / "no-temp")):
            self.assertIn("program folder", apps.place_risk(library))
            self.assertIsNone(apps.place_risk(cloud))
            self.assertIn("hidden program folder", apps.place_risk(hidden))


class MovingProgramDataTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.vault = self.make_file("Notes/.obsidian/app.json").parent.parent
        self.note = self.vault / "idea.md"
        self.note.write_text("x")
        (self.root / "Archive").mkdir()
        self.target = self.root / "Archive/idea.md"

    def ctx(self):
        return apps.Context([], {})

    def test_move_is_refused_and_nothing_changes(self):
        with self.assertRaises(FilingError) as err:
            fileops.move(self.note, self.target, ctx=self.ctx())

        self.assertIn("a program may stop working", str(err.exception))
        self.assertTrue(self.note.exists())

    def test_app_data_flag_moves_anyway(self):
        fileops.move(self.note, self.target, app_data=True)

        self.assertTrue(self.target.exists())

    def test_trash_of_program_data_is_refused(self):
        with self.assertRaises(FilingError):
            fileops.trash(self.note, ctx=self.ctx())

    def test_filing_into_a_program_library_is_refused(self):
        letter = self.make_file("Downloads/letter.pdf")

        with self.assertRaises(FilingError):
            fileops.move(letter, self.vault / "letter.pdf", ctx=self.ctx())

    @unittest.skipUnless(CAN_LINK, "symlinks")
    def test_leave_link_keeps_the_program_working_and_undo_restores(self):
        fileops.move(self.note, self.target, leave_link=True, ctx=self.ctx())

        self.assertTrue(self.note.is_symlink())
        self.assertEqual(self.note.read_text(), "x")   # the program still finds its file
        undo.undo(last=1)
        self.assertFalse(self.note.is_symlink())
        self.assertTrue(self.note.is_file())
        self.assertFalse(self.target.exists())

    def test_without_symlink_rights_a_hard_link_keeps_the_file_reachable(self):
        with mock.patch.object(apps.os, "symlink", side_effect=OSError("privilege not held")):
            fileops.move(self.note, self.target, leave_link=True, ctx=self.ctx())

        self.assertFalse(self.note.is_symlink())
        self.assertTrue(os.path.samefile(self.note, self.target))   # same file, reachable at both places
        undo.undo(last=1)
        self.assertTrue(self.note.is_file())
        self.assertFalse(self.target.exists())

    @unittest.skipUnless(os.name == "nt", "junctions exist only on Windows")
    def test_folder_link_falls_back_to_a_junction_on_windows(self):
        folder = self.vault
        target = self.root / "Archive" / "Notes"
        with mock.patch.object(apps.os, "symlink", side_effect=OSError("privilege not held")):
            fileops.move(folder, target, leave_link=True, app_data=True)

        self.assertTrue((folder / "idea.md").exists())
        undo.undo(last=1)
        self.assertTrue((folder / "idea.md").exists())
        self.assertFalse(target.exists())

    @unittest.skipUnless(CAN_LINK, "symlinks")
    def test_plan_flags_program_data_and_link_mark_applies(self):
        plan_file = self.root / "plan.md"
        plan.add(plan_file, self.note, self.target, "note")

        self.assertIn("program may stop working", plan.check(plan_file)[0][1])
        plan.approve(plan_file, link=True)
        self.assertIsNone(plan.check(plan_file)[0][1])
        self.assertEqual(plan.apply(plan_file).done, 1)
        self.assertTrue(self.note.is_symlink())


if __name__ == "__main__":
    unittest.main()
