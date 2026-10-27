import asyncio
import importlib.util
import unittest

from aichivist import agent_tools, catalog, fileops
from helpers import SandboxTest

HAS_MCP = importlib.util.find_spec("mcp") is not None


class WorkspaceTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.inbox = self.root / "Downloads"
        self.archive = self.root / "archive"
        self.make_file("Downloads/scan_0042.txt", b"Example Health policy valid from 2026-01-01")
        (self.archive / "Insurance").mkdir(parents=True)
        self.rules = self.make_file("rules.md", b"# Rules\nPersonal papers -> archive/<Subject>/\n")
        self.ws = agent_tools.Workspace([self.inbox, self.archive], self.rules)

    def test_paths_outside_the_allowed_folders_are_refused(self):
        secret = self.make_file("private/diary.txt", b"secret")

        with self.assertRaises(fileops.FilingError):
            self.ws.read_document(str(secret))
        with self.assertRaises(fileops.FilingError):
            self.ws.read_document(str(self.inbox / ".." / "private" / "diary.txt"))

    def test_read_document_returns_text_and_method(self):
        result = self.ws.read_document(str(self.inbox / "scan_0042.txt"))

        self.assertIn("Example Health", result["text"])
        self.assertEqual(result["method"], "text")

    def test_long_documents_are_truncated_and_say_so(self):
        self.make_file("Downloads/long.txt", b"x" * 50_000)

        result = self.ws.read_document(str(self.inbox / "long.txt"), max_chars=1000)

        self.assertEqual(len(result["text"]), 1000)
        self.assertTrue(result["truncated"])

    def test_rules_are_served_to_the_agent(self):
        self.assertIn("Personal papers", self.ws.get_rules()["rules"])

    def test_plan_lifecycle_through_named_plans(self):
        target = str(self.archive / "Insurance/2026-01-01 Example Health policy.txt")
        self.ws.plan_add(str(self.inbox / "scan_0042.txt"), target, "health policy")

        self.assertEqual(self.ws.plan_check()["problems"], [])
        self.assertEqual(self.ws.plan_show()["rows"][0]["mark"], "?")
        self.ws.plan_approve()
        result = self.ws.plan_apply()

        self.assertEqual(result["done"], 1)
        self.assertTrue((self.archive / "Insurance/2026-01-01 Example Health policy.txt").exists())

    def test_plan_targets_outside_the_allowed_folders_are_refused(self):
        with self.assertRaises(fileops.FilingError):
            self.ws.plan_add(str(self.inbox / "scan_0042.txt"), str(self.root / "elsewhere/x.txt"), "escape")

    def test_list_folder_shows_entries(self):
        result = self.ws.list_folder(str(self.inbox))

        self.assertEqual([e["name"] for e in result["entries"]], ["scan_0042.txt"])


class ExcludedZonesTest(SandboxTest):
    def setUp(self):
        super().setUp()
        self.docs = self.root / "Documents"
        self.make_file("Documents/Insurance/policy.txt", b"policy")
        self.make_file("Documents/Health/diagnosis.txt", b"private diagnosis")
        self.ws = agent_tools.Workspace([self.docs], None, exclude=[self.docs / "Health"])

    def test_excluded_files_cannot_be_read(self):
        with self.assertRaises(fileops.FilingError):
            self.ws.read_document(str(self.docs / "Health/diagnosis.txt"))

    def test_excluded_folders_are_invisible_in_listings_and_survey(self):
        names = [e["name"] for e in self.ws.list_folder(str(self.docs))["entries"]]
        report = self.ws.survey([str(self.docs)])

        self.assertEqual(names, ["Insurance"])
        self.assertEqual(report["locations"][0]["files"], 1)
        self.assertNotIn("diagnosis", str(report))
        self.assertNotIn("diagnosis", str(self.ws.inventory(str(self.docs))))

    def test_excluded_folder_is_not_a_valid_plan_target(self):
        with self.assertRaises(fileops.FilingError):
            self.ws.plan_add(str(self.docs / "Insurance/policy.txt"), str(self.docs / "Health/policy.txt"), "x")


class CatalogDescribeTest(SandboxTest):
    def test_describe_replaces_the_placeholder_row(self):
        self.make_file("Area/_catalog.md", b"| File | Content |\n|---|---|\n")
        self.make_file("Area/a.pdf")
        catalog.add_missing(self.root / "Area/_catalog.md")

        catalog.describe(self.root / "Area/_catalog.md", "a.pdf", "health policy", "health, insurance", "2026-01-01")

        text = (self.root / "Area/_catalog.md").read_text(encoding="utf-8")
        self.assertIn("| a.pdf | health policy | health, insurance | 2026-01-01 |", text)
        self.assertNotIn(catalog.TO_DESCRIBE, text)

    def test_describe_without_placeholder_is_refused(self):
        self.make_file("Area/_catalog.md", b"| File | Content |\n|---|---|\n")

        with self.assertRaises(fileops.FilingError):
            catalog.describe(self.root / "Area/_catalog.md", "a.pdf", "x", "y", "z")


@unittest.skipUnless(HAS_MCP, "mcp not installed")
class McpServerTest(SandboxTest):
    def test_server_lists_tools_and_answers_a_call(self):
        from aichivist import mcp_server
        inbox = self.root / "Downloads"
        self.make_file("Downloads/a.txt", b"hello archive")
        server = mcp_server.build(agent_tools.Workspace([inbox], None))

        names = {t.name for t in asyncio.run(server.list_tools())}
        result = asyncio.run(server.call_tool("read_document", {"path": str(inbox / "a.txt")}))

        self.assertTrue({"survey", "read_document", "plan_add", "plan_apply", "search"} <= names)
        hints = {t.name: t.annotations for t in asyncio.run(server.list_tools())}
        read_only = getattr(hints["read_document"], "read_only_hint", None) or getattr(hints["read_document"],
                                                                                       "readOnlyHint", None)
        destructive = getattr(hints["plan_apply"], "destructive_hint", None) or getattr(hints["plan_apply"],
                                                                                         "destructiveHint", None)
        self.assertTrue(read_only)
        self.assertTrue(destructive)
        self.assertIn("hello archive", str(result))


if __name__ == "__main__":
    unittest.main()
