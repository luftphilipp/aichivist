import os
import struct
import time
import unittest
from datetime import datetime

from aichivist import photos, plan
from helpers import SandboxTest


def jpeg_taken(stamp="2021:07:14 10:00:00"):
    """A minimal JPEG whose EXIF block holds DateTimeOriginal."""
    tiff = (b"II*\x00" + struct.pack("<I", 8)
            + struct.pack("<H", 1) + struct.pack("<HHII", 0x8769, 4, 1, 26) + struct.pack("<I", 0)
            + struct.pack("<H", 1) + struct.pack("<HHII", 0x9003, 2, 20, 44) + struct.pack("<I", 0)
            + stamp.encode() + b"\x00")
    app1 = b"Exif\x00\x00" + tiff
    return b"\xff\xd8\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1 + b"\xff\xd9"


def mp4_taken(when=datetime(2019, 5, 1, 12)):
    seconds = int((when - photos.MAC_EPOCH).total_seconds())
    mvhd = struct.pack(">I4sB3sI", 8 + 1 + 3 + 4 + 80, b"mvhd", 0, b"\x00\x00\x00", seconds) + b"\x00" * 80
    moov = struct.pack(">I4s", 8 + len(mvhd), b"moov") + mvhd
    return struct.pack(">I4s4s", 12, b"ftyp", b"isom") + moov


class PhotoDateTest(SandboxTest):
    def test_camera_date_from_jpeg_exif(self):
        f = self.make_file("in/IMG_0001.jpg", jpeg_taken())

        self.assertEqual(photos.date_taken(f), ("2021-07-14", "camera"))

    def test_camera_date_from_video_header(self):
        f = self.make_file("in/clip.mp4", mp4_taken())

        self.assertEqual(photos.date_taken(f), ("2019-05-01", "camera"))

    def test_file_name_date_when_the_camera_date_is_missing(self):
        f = self.make_file("in/IMG-20230812-WA0003.jpg", b"\xff\xd8\xff\xd9")

        self.assertEqual(photos.date_taken(f), ("2023-08-12", "file name"))

    def test_modified_date_as_last_resort(self):
        f = self.make_file("in/holiday.jpg", b"not really a jpeg")
        stamp = time.mktime((2018, 3, 4, 12, 0, 0, 0, 0, -1))
        os.utime(f, (stamp, stamp))

        self.assertEqual(photos.date_taken(f), ("2018-03-04", "modified date"))


class PhotoPlanTest(SandboxTest):
    def test_photos_are_proposed_by_year_and_subject_and_moved_after_approval(self):
        self.make_file("in/IMG_0001.jpg", jpeg_taken())
        self.make_file("in/Holidays Ticino/clip.mp4", mp4_taken())
        self.make_file("in/notes.txt", b"not a photo")
        (self.root / "Photos").mkdir()
        plan_file = self.root / "plan.md"

        rows = photos.propose(self.root / "in", self.root / "Photos", plan_file)

        self.assertEqual(sorted(os.path.relpath(r.target, self.root / "Photos") for r in rows),
                         [os.path.join("2019", "Holidays Ticino", "clip.mp4"), os.path.join("2021", "IMG_0001.jpg")])
        self.assertIn("folder missing", plan.check(plan_file)[0][1])
        self.assertIsNone(plan.check(plan_file, create_folders=True)[0][1])
        plan.approve(plan_file)
        self.assertEqual(plan.apply(plan_file, create_folders=True).done, 2)
        self.assertTrue((self.root / "Photos/2021/IMG_0001.jpg").exists())


if __name__ == "__main__":
    unittest.main()
