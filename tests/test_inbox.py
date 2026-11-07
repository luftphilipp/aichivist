"""Inbox realities from a field session: screenshots, secrets on screen, running downloads, films in Downloads."""
import errno
import os
import time
from unittest import mock

from test_commands import run

from aichivist import describe, fileops, inbox, inventory, sensitive, triage
from helpers import SandboxTest

# invented token: {"aud":"example-not-a-real-key","sub":"alex-sample"}
JWT = ("eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJleGFtcGxlLW5vdC1hLXJlYWwta2V5Iiwic3ViIjoiYWxleC1zYW1wbGUifQ"
       ".ZXhhbXBsZS1zaWduYXR1cmUtb25seQ")
EXDEV = OSError(errno.EXDEV, "cross-device")


class SensitiveTest(SandboxTest):
    def test_tokens_keys_and_codes_are_named_without_repeating_them(self):
        found = sensitive.find(f"API-Token für Lesezugriff {JWT}")

        self.assertIn("access token", found)
        self.assertFalse(any(JWT[:12] in reason for reason in found))

    def test_labels_and_card_like_numbers_count(self):
        self.assertIn("account key", sensitive.find("You're all set. Here's your account key 1234 5678 9012 3456"))
        self.assertIn("recovery codes", sensitive.find("GitHub recovery codes\n1a2b3-c4d5e"))
        self.assertIn("private key", sensitive.find("-----BEGIN OPENSSH PRIVATE KEY-----"))

    def test_ordinary_documents_are_not_flagged(self):
        self.assertEqual(sensitive.find("Example Bank AG\nStatement 2026-03-31\nIBAN CH93 0076 2011 6238 5295 7"), [])

    def test_redact_hides_the_secret_itself(self):
        text = sensitive.redact(f"API-Token {JWT} end")

        self.assertNotIn(JWT[:20], text)
        self.assertIn("end", text)


class ScreenshotSuggestTest(SandboxTest):
    def test_screenshot_without_a_document_is_marked_temporary(self):
        shot = self.make_file("Downloads/Bildschirmfoto 2026-11-03 um 21.20.15.png", b"png")

        s = describe.suggest(shot, text="Error 1101 Worker threw exception What happened?")

        self.assertEqual(s["kind"], "Screenshot")
        self.assertEqual(s["date"], "2026-11-03")
        self.assertTrue(s["temporary"])

    def test_screenshot_of_a_secret_is_flagged_and_its_summary_redacted(self):
        shot = self.make_file("Downloads/Screenshot 2026-11-03 at 15.47.05.png", b"png")

        s = describe.suggest(shot, text=f"API token for read access {JWT}")

        self.assertIn("access token", s["sensitive"])
        self.assertNotIn(JWT[:20], s["summary"] + " ".join(s["keywords"]))

    def test_rows_carry_the_new_marks_only_when_they_apply(self):
        self.make_file("Downloads/Bildschirmfoto 2026-11-04 um 10.33.59.png", b"png")
        self.make_file("Downloads/invoice.txt", b"Example Shop AG\nInvoice 2026-02-01\nHeadphones")

        with mock.patch("aichivist.fulltext._ocr", return_value=("concurrency limit reached", "ocr")):
            rows = {r["file"]: r for r in describe.rows(describe.visible_files([self.root / "Downloads"]))}

        self.assertTrue(rows["Bildschirmfoto 2026-11-04 um 10.33.59.png"]["temporary"])
        self.assertNotIn("temporary", rows["invoice.txt"])
        self.assertNotIn("sensitive", rows["invoice.txt"])


class DownloadsInProgressTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.inbox = self.root / "Downloads"
        self.bundle = self.make_file("Downloads/Film (2001).mkv.download/Film (2001).mkv", b"x" * 100).parent
        self.make_file("Downloads/Film (2001).mkv.download/Info.plist", b"<plist/>")
        self.make_file("Downloads/clip.mp4.crdownload", b"x" * 50)

    def test_partial_downloads_are_recognised(self):
        self.assertTrue(inbox.is_partial(self.bundle))
        self.assertTrue(inbox.is_partial(self.inbox / "clip.mp4.crdownload"))
        self.assertFalse(inbox.is_partial(self.make_file("Downloads/report.pdf")))

    def test_a_download_without_progress_for_minutes_counts_as_stalled(self):
        old = time.time() - inbox.STALL_SECONDS - 60
        for f in self.bundle.iterdir():
            os.utime(f, (old, old))

        self.assertEqual(inbox.download_state(self.bundle), "stalled")
        self.assertEqual(inbox.download_state(self.inbox / "clip.mp4.crdownload"), "downloading")

    def test_inventory_lists_downloads_apart_and_does_not_read_them(self):
        self.make_file("Downloads/letter.pdf", b"letter")

        with mock.patch("aichivist.inventory.digest", wraps=inventory.digest) as hashed:
            changes = inventory.diff(self.inbox)
        downloads = inventory.downloads(self.inbox, changes)

        self.assertEqual({d["path"] for d in downloads}, {"Film (2001).mkv.download/", "clip.mp4.crdownload"})
        self.assertEqual([c.args[0].name for c in hashed.call_args_list], ["letter.pdf"])
        self.assertNotIn("Film (2001).mkv.download/Info.plist", changes.entries)

    def test_inventory_command_shows_downloading_instead_of_new(self):
        run("inventory", str(self.inbox), "--save")
        self.make_file("Downloads/other.mkv.part", b"x")

        code, out = run("inventory", str(self.inbox))

        self.assertIn("DOWNLOADING\tother.mkv.part", out)
        self.assertNotIn("NEW\tother.mkv.part", out)

    def test_trash_refuses_a_download_that_is_still_running(self):
        with self.assertRaises(fileops.FilingError) as err:
            fileops.trash(self.bundle)

        self.assertIn("still downloading", str(err.exception))
        self.assertTrue(self.bundle.exists())

    def test_trash_takes_a_running_download_when_asked(self):
        target = fileops.trash(self.bundle, downloading=True)

        self.assertTrue(target.exists())

    def test_suggest_skips_partial_downloads(self):
        names = {f.name for f in describe.visible_files([self.inbox])}

        self.assertNotIn("clip.mp4.crdownload", names)


class TrashSummaryTest(SandboxTest):
    def test_several_files_in_one_call_end_with_a_total(self):
        a = self.make_file("Downloads/a.png", b"x" * 1000)
        b = self.make_file("Downloads/b.png", b"x" * 2000)

        code, out = run("trash", str(a), str(b))

        self.assertEqual(code, 0)
        self.assertIn("2 items (2.9 KB) moved to the trash", out)


class DriveFlagsTest(SandboxTest):
    def test_drives_answering_operation_not_supported_keep_content_and_dates(self):
        src = self.make_file("inbox/a.pdf", b"x" * 10)
        (self.root / "drive").mkdir()
        refused = OSError(errno.EOPNOTSUPP, "Operation not supported on socket")

        with mock.patch("aichivist.fileops.os.rename", side_effect=EXDEV), \
                mock.patch("shutil.copystat", side_effect=refused):
            fileops.move(src, self.root / "drive/a.pdf")

        self.assertEqual((self.root / "drive/a.pdf").read_bytes(), b"x" * 10)


class MediaTest(SandboxTest):
    def test_release_names_are_films_or_episodes_and_phone_clips_personal_videos(self):
        self.assertEqual(inbox.media_kind(self.root / "The.Godfather.1972.2160p.UHD.BluRay.REMUX.mkv"), "film")
        self.assertEqual(inbox.media_kind(self.root / "Hannibal (2013) - S03E10 - Title [Bluray-1080p].mkv"),
                         "episode")
        self.assertEqual(inbox.media_kind(self.root / "IMG_1234.MOV"), "personal video")
        self.assertIsNone(inbox.media_kind(self.root / "report.pdf"))


class TriageTest(SandboxTest):
    def test_one_call_sorts_an_inbox_into_what_to_do(self):
        d = self.root / "Downloads"
        self.make_file("Downloads/Bildschirmfoto 2026-11-05 um 21.34.44.png", b"png")
        self.make_file("Downloads/Screenshot 2026-11-03 at 15.47.05.png", b"png")
        self.make_file("Downloads/invoice.txt", b"Example Shop AG\nInvoice 2026-02-01\nHeadphones")
        self.make_file("Downloads/Setup.dmg", b"dmg")
        self.make_file("Downloads/Some.Film.2014.1080p.BluRay.x264.mkv", b"mkv")
        self.make_file("Downloads/clip.mp4.crdownload", b"x")
        texts = {"Bildschirmfoto 2026-11-05 um 21.34.44.png": "Message to the hiring team",
                 "Screenshot 2026-11-03 at 15.47.05.png": f"API token {JWT}"}

        with mock.patch("aichivist.fulltext._ocr", side_effect=lambda p: (texts[p.name], "ocr")):
            rows = {r["file"]: r for r in triage.run(d)}

        self.assertEqual(rows["Bildschirmfoto 2026-11-05 um 21.34.44.png"]["category"], "temporary")
        self.assertEqual(rows["Screenshot 2026-11-03 at 15.47.05.png"]["category"], "sensitive")
        self.assertEqual(rows["invoice.txt"]["category"], "document")
        self.assertIn("Invoice", rows["invoice.txt"]["suggested_name"])
        self.assertEqual(rows["Setup.dmg"]["category"], "installer")
        self.assertEqual(rows["Some.Film.2014.1080p.BluRay.x264.mkv"]["category"], "film")
        self.assertEqual(rows["clip.mp4.crdownload"]["category"], "downloading")

    def test_triage_command_prints_a_line_per_file_and_changes_nothing(self):
        self.make_file("Downloads/Setup.pkg", b"pkg")

        code, out = run("triage", str(self.root / "Downloads"))

        self.assertEqual(code, 0)
        self.assertIn("installer", out)
        self.assertTrue((self.root / "Downloads/Setup.pkg").exists())
