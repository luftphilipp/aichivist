"""Shared test setup: every test runs in its own temporary home, log and trash."""
import os
import tempfile
import unittest
from pathlib import Path


class SandboxTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.home = self.root / "state"
        self.trash = self.root / "trash"
        self.trash.mkdir()
        self._old_env = {k: os.environ.get(k) for k in ("AICHIVIST_HOME", "AICHIVIST_TRASH", "AICHIVIST_LANG")}
        os.environ["AICHIVIST_HOME"] = str(self.home)
        os.environ["AICHIVIST_TRASH"] = str(self.trash)
        os.environ["AICHIVIST_LANG"] = "en"  # messages are checked in English; German has its own tests

    def tearDown(self):
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()

    def make_file(self, rel, content=b"data"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path
