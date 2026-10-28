"""Token economy: short reads by default, one call for many files, compact tool definitions and results."""
import asyncio
import importlib.util
import json
import unittest
from unittest import mock

import aichivist
from aichivist import agent_tools, mcp_server
from helpers import SandboxTest

HAS_MCP = importlib.util.find_spec("mcp") is not None


class ShortReadsTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.inbox = self.root / "Downloads"
        self.make_file("Downloads/long.txt", ("first page " * 1000 + "LATER").encode())
        self.ws = agent_tools.Workspace([self.inbox])

    def test_a_document_is_read_short_by_default_and_can_be_continued(self):
        first = self.ws.read_document(str(self.inbox / "long.txt"))
        rest = self.ws.read_document(str(self.inbox / "long.txt"), offset=first["next_offset"], max_chars=20_000)

        self.assertLessEqual(len(first["text"]), agent_tools.DEFAULT_MAX_CHARS)
        self.assertLessEqual(agent_tools.DEFAULT_MAX_CHARS, 3000)
        self.assertTrue(first["truncated"])
        self.assertTrue(rest["text"].endswith("LATER"))
        self.assertIsNone(rest["next_offset"])

    def test_one_call_suggests_names_for_many_files(self):
        self.make_file("Downloads/scan_0042.txt", b"Example Health Insurance\nPolicy 2026-01-01\nHousehold cover")
        self.make_file("Downloads/.hidden.txt", b"x")
        (self.inbox / "sub").mkdir()

        rows = self.ws.suggest_names([str(self.inbox)])

        names = {r["file"] for r in rows}
        self.assertIn("scan_0042.txt", names)
        self.assertNotIn(".hidden.txt", names)
        row = next(r for r in rows if r["file"] == "scan_0042.txt")
        self.assertEqual(set(row), {"file", "folder", "date", "issuer", "kind", "suggested_name", "confident"})

    def test_long_folder_listings_are_cut_with_a_count(self):
        for n in range(agent_tools.LIST_LIMIT + 5):
            self.make_file(f"Downloads/many/f{n:04}.txt")

        result = self.ws.list_folder(str(self.inbox / "many"))

        self.assertEqual(len(result["entries"]), agent_tools.LIST_LIMIT)
        self.assertEqual(result["total"], agent_tools.LIST_LIMIT + 5)
        self.assertLessEqual(agent_tools.LIST_LIMIT, 100)


class BatchSuggestCommandTest(SandboxTest):
    def test_suggest_takes_a_whole_folder_in_one_call(self):
        from test_commands import run
        self.make_file("Downloads/a.txt", b"Example Bank\nStatement 2026-03-31")
        self.make_file("Downloads/b.txt", b"Example Rail\nTicket 2026-04-01")

        code, out = run("--json", "suggest", str(self.root / "Downloads"))

        rows = json.loads(out)["data"]
        self.assertEqual(code, 0)
        self.assertEqual(sorted(r["file"] for r in rows), ["a.txt", "b.txt"])


class ServerOptionsTest(unittest.TestCase):
    def test_empty_settings_count_as_not_set(self):
        with mock.patch.object(mcp_server, "build") as build, \
                mock.patch.object(mcp_server, "Workspace") as workspace:
            mcp_server.serve(["/data", ""], "", ["", "/data/private"])

        workspace.assert_called_once_with(["/data"], None, ["/data/private"])
        build.return_value.run.assert_called_once()


@unittest.skipUnless(HAS_MCP, "mcp not installed")
class CompactToolsTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.server = mcp_server.build(agent_tools.Workspace([self.root]))
        self.tools = asyncio.run(self.server.list_tools())

    def test_every_tool_has_a_title_and_no_output_schema(self):
        for tool in self.tools:
            title = tool.title or getattr(tool.annotations, "title", None)
            self.assertTrue(title, tool.name)
            self.assertIsNone(getattr(tool, "outputSchema", None) or getattr(tool, "output_schema", None), tool.name)

    def test_tool_definitions_stay_small(self):
        size = sum(len(json.dumps(t.model_dump(exclude_none=True))) for t in self.tools)

        self.assertLess(size, 12_000)  # was 15,800 before descriptions were cut and output schemas dropped

    def test_results_are_compact_json(self):
        self.make_file("a.txt", b"hello archive")

        result = asyncio.run(self.server.call_tool("list_folder", {"path": str(self.root)}))

        text = str(result)
        self.assertIn("a.txt", text)
        self.assertNotIn('\\n  "', text)  # no indented JSON

    def test_server_reports_its_version(self):
        self.assertEqual(mcp_server.server_version(self.server), aichivist.__version__)


if __name__ == "__main__":
    unittest.main()
