import os
import re
import string
import unittest
from pathlib import Path
from unittest import mock

from aichivist import apps, i18n, storage, structure, survey
from aichivist.lang_de import GERMAN
from helpers import SandboxTest

SOURCE = Path(__file__).resolve().parent.parent / "aichivist"
SINGLE_LITERAL = re.compile(r'\bt_?\("((?:[^"\\]|\\.)*)"[,)]')


def fields(text):
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


class LanguageTest(SandboxTest):
    def test_german_and_swiss_spelling(self):
        with mock.patch.dict(os.environ, {"AICHIVIST_LANG": "de_DE"}):
            self.assertEqual(i18n.t("{n} rows approved", n=3), "3 Zeilen freigegeben")
            self.assertIn("außer", i18n.t("{area}: {copies} copies on {kinds} kind(s), {away} away from home – "
                                          "{status}", area="A", copies=1, kinds=1, away=0, status="x"))
        with mock.patch.dict(os.environ, {"AICHIVIST_LANG": "de_CH"}):
            self.assertIn("ausser", i18n.t("{area}: {copies} copies on {kinds} kind(s), {away} away from home – "
                                           "{status}", area="A", copies=1, kinds=1, away=0, status="x"))

    def test_system_language_is_used_when_nothing_is_chosen(self):
        unset = {"AICHIVIST_LANG": "", "LC_ALL": "", "LC_MESSAGES": ""}
        with mock.patch.dict(os.environ, {**unset, "LANG": "de_AT.UTF-8"}):
            self.assertEqual(i18n.language(), "de")
        with mock.patch.dict(os.environ, {**unset, "LANG": "fr_FR"}):
            self.assertEqual(i18n.language(), "en")

    def test_counts_in_german(self):
        with mock.patch.dict(os.environ, {"AICHIVIST_LANG": "de"}):
            self.assertEqual(i18n.count(1, "file"), "1 Datei")
            self.assertEqual(i18n.count(1200, "file"), "1 200 Dateien")


class DictionaryTest(unittest.TestCase):
    def test_translations_keep_every_field(self):
        for english, german in GERMAN.items():
            self.assertEqual(fields(english), fields(german), english)

    def test_every_single_line_message_in_the_code_is_translated(self):
        missing = set()
        for path in SOURCE.glob("*.py"):
            for match in SINGLE_LITERAL.finditer(path.read_text(encoding="utf-8")):
                text = match.group(1).encode().decode("unicode_escape").encode("latin-1").decode("utf-8")
                if text not in GERMAN:
                    missing.add(f"{path.name}: {text}")
        self.assertEqual(missing, set())

    def test_messages_kinds_and_titles_are_translated(self):
        keys = (list(structure.MESSAGES.values()) + list(structure.TITLES.values())
                + list(apps.LIBRARY_SUFFIXES.values()) + list(apps.FOLDER_MARKERS.values())
                + ["passed", "failed", "unknown", "open", "closed", "camera", "file name", "modified date",
                   "NEW", "CHANGED", "REMOVED"])
        self.assertEqual([k for k in keys if k not in GERMAN], [])

    def test_german_reports_render(self):
        with mock.patch.dict(os.environ, {"AICHIVIST_LANG": "de"}):
            lines = storage.render(storage.Report([], {"Cloud": 34.8}, []), "CHF")
        self.assertTrue(lines[0].startswith("Kosten pro Jahr"))
        self.assertIsNotNone(survey)


if __name__ == "__main__":
    unittest.main()
