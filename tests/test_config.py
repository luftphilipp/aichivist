import errno
import os
import unittest
from pathlib import Path
from unittest import mock

from aichivist import config, fileops


class TrashLocationTest(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.pop("AICHIVIST_TRASH", None)

    def tearDown(self):
        if self._saved is not None:
            os.environ["AICHIVIST_TRASH"] = self._saved

    def test_macos_uses_user_trash(self):
        with mock.patch.object(config.sys, "platform", "darwin"):
            self.assertEqual(config.trash_dir(), Path.home() / ".Trash")

    def test_linux_uses_freedesktop_trash(self):
        with mock.patch.object(config.sys, "platform", "linux"), \
                mock.patch.dict(os.environ, {"XDG_DATA_HOME": "/data"}):
            self.assertEqual(config.trash_dir(), Path("/data/Trash/files"))

    def test_windows_uses_own_restorable_trash(self):
        with mock.patch.object(config.sys, "platform", "win32"), \
                mock.patch.dict(os.environ, {"AICHIVIST_HOME": "C:/state"}):
            self.assertEqual(config.trash_dir(), Path("C:/state/trash"))

    def test_environment_override_wins(self):
        with mock.patch.dict(os.environ, {"AICHIVIST_TRASH": "/custom"}):
            self.assertEqual(config.trash_dir(), Path("/custom"))


class CrossDeviceErrorTest(unittest.TestCase):
    def test_recognises_unix_and_windows_cross_drive_errors(self):
        unix = OSError(errno.EXDEV, "cross-device link")
        windows = OSError(0, "different disk drive")
        windows.winerror = 17
        other = OSError(errno.EACCES, "denied")

        self.assertTrue(fileops.is_cross_device(unix))
        self.assertTrue(fileops.is_cross_device(windows))
        self.assertFalse(fileops.is_cross_device(other))


if __name__ == "__main__":
    unittest.main()
