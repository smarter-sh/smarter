"""Tests for smarter.apps.mcpserver.protocol.tools, the base class of every tool, and smarter.apps.mcpserver.protocol.registry."""

from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.index.tools import (
    ReadFileTool,
    SearchDocumentationTool,
)
from smarter.apps.mcpserver.protocol.registry import TOOL_CLASSES
from smarter.apps.mcpserver.protocol.tools import simplify_schema

from .base_classes import MCPServerTestBase


class TestTools(MCPServerTestBase):
    """Test what every tool of the MCP server of one repository, and of all of them, has in common."""

    # -------------------------------------------------------------------------
    # schemas and scopes
    # -------------------------------------------------------------------------
    def test_input_schema_of_one_repository(self):
        """The MCP server of one repository offers no repository argument."""
        for tool_class in TOOL_CLASSES:
            with self.subTest(tool=tool_class.name):
                schema = tool_class(self.single()).input_schema()
                self.assertEqual(schema["type"], "object")
                self.assertFalse(schema["additionalProperties"])
                self.assertNotIn("repository", schema["properties"])
                self.assertNotIn("title", schema)
                self.assertNotIn("description", schema)
                for prop in schema["properties"].values():
                    self.assertNotIn("anyOf", prop)
                    self.assertNotIn("title", prop)

    def test_input_schema_of_all_repositories(self):
        """The MCP server of all of the repositories names them, and requires one where a tool needs it."""
        names = [repository.name for repository in self.repositories]
        for tool_class in TOOL_CLASSES:
            with self.subTest(tool=tool_class.name):
                schema = tool_class(self.all()).input_schema()
                if not tool_class.uses_repository:
                    self.assertNotIn("repository", schema["properties"])
                    continue
                self.assertEqual(schema["properties"]["repository"]["enum"], names)
                self.assertEqual("repository" in schema.get("required", []), tool_class.requires_repository)
        self.assertEqual(ReadFileTool(self.all()).input_schema()["required"], ["repository", "path"])

    def test_definition(self):
        """Only the GitHub tools reach beyond the platform, and only the operations write."""
        writes = {"create_issue", "comment_on_issue", "close_issue", "create_pull_request"}
        open_world = writes | {"search_issues", "read_issue"}
        for tool_class in TOOL_CLASSES:
            with self.subTest(tool=tool_class.name):
                definition = tool_class(self.single()).definition()
                self.assertEqual(definition.name, tool_class.name)
                self.assertEqual(definition.annotations.read_only_hint, tool_class.name not in writes)
                self.assertEqual(definition.annotations.idempotent_hint, tool_class.name not in writes)
                self.assertEqual(definition.annotations.open_world_hint, tool_class.name in open_world)
                self.assertFalse(definition.annotations.destructive_hint)

    def test_simplify_schema(self):
        """Optional fields lose their null variant and null default."""
        schema = simplify_schema(
            {
                "title": "X",
                "description": "doc",
                "properties": {"a": {"title": "A", "anyOf": [{"type": "string"}, {"type": "null"}], "default": None}},
            }
        )
        self.assertEqual(schema, {"properties": {"a": {"type": "string"}}})

    def test_scope_resolve(self):
        """A tool call names one of the scope's repositories, or none."""
        scope = self.all()
        self.assertEqual(scope.resolve(self.code_repository.name, required=True), self.code_repository)
        self.assertIsNone(scope.resolve(None, required=False))
        with self.assertRaises(SmarterMCPServerToolError):
            scope.resolve(None, required=True)
        with self.assertRaises(SmarterMCPServerToolError):
            scope.resolve("smarter-not-a-repository", required=False)
        self.assertEqual(self.single().resolve(self.code_repository.name, required=True), self.docs_repository)

    def test_invalid_arguments(self):
        """Arguments are validated, and the problems are explained."""
        tool = SearchDocumentationTool(self.single())
        with self.assertRaisesRegex(SmarterMCPServerToolError, "query"):
            tool.call({})
        with self.assertRaisesRegex(SmarterMCPServerToolError, "limit"):
            tool.call({"query": "x", "limit": 1000})
        with self.assertRaisesRegex(SmarterMCPServerToolError, "unexpected"):
            tool.call({"query": "x", "unexpected": True})

    def test_single_scope_ignores_repository(self):
        """The MCP server of one repository ignores a repository argument."""
        text = SearchDocumentationTool(self.single()).call({"query": "custom domain", "repository": "anything"})
        self.assertIn("custom-domains.rst", text)
