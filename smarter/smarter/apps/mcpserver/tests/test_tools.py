"""Tests for smarter.apps.mcpserver.tools."""

from unittest import mock

from smarter.apps.mcpserver import tools
from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.tools import (
    TOOL_CLASSES,
    GetRepositoryOverviewTool,
    ListFilesTool,
    ReadFileTool,
    SearchCodeTool,
    SearchDocumentationTool,
    SmarterProjectScope,
    simplify_schema,
)

from .base_classes import COMMIT_SHA, DOCS_URL, MCPServerTestBase


class TestTools(MCPServerTestBase):
    """Test the tools of the MCP server of one repository, and of all of them."""

    def single(self, repository=None) -> SmarterProjectScope:
        repository = repository or self.docs_repository
        return SmarterProjectScope(repository=repository, repositories=(repository,))

    def all(self) -> SmarterProjectScope:
        return SmarterProjectScope(repository=None, repositories=self.repositories)

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
                self.assertEqual(schema["properties"]["repository"]["enum"], names)
                self.assertEqual("repository" in schema.get("required", []), tool_class.requires_repository)
        self.assertEqual(ReadFileTool(self.all()).input_schema()["required"], ["repository", "path"])

    def test_definition(self):
        """Every tool is read-only, idempotent and closed-world."""
        for tool_class in TOOL_CLASSES:
            definition = tool_class(self.single()).definition()
            self.assertEqual(definition.name, tool_class.name)
            self.assertTrue(definition.annotations.read_only_hint)
            self.assertFalse(definition.annotations.destructive_hint)
            self.assertFalse(definition.annotations.open_world_hint)

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

    # -------------------------------------------------------------------------
    # get_repository_overview
    # -------------------------------------------------------------------------
    def test_overview(self):
        """A repository's overview has its links, commit, layout and README."""
        text = GetRepositoryOverviewTool(self.single()).call({})
        self.assertIn(f"# {self.docs_repository.name}: the test platform", text)
        self.assertIn(self.docs_repository.github_url, text)
        self.assertIn(f"Published documentation: {DOCS_URL}", text)
        self.assertIn(COMMIT_SHA, text)
        self.assertIn("- docs/ (3 files)", text)
        self.assertIn("## README.md", text)
        self.assertIn("governed AI applications", text)

    def test_overview_truncates_the_readme(self):
        """A long README is truncated."""
        with mock.patch.object(tools, "MAX_README_CHARACTERS", 10):
            text = GetRepositoryOverviewTool(self.single()).call({})
        self.assertIn("[README truncated", text)

    def test_overview_of_all_repositories(self):
        """Without a repository, the overview is a table of every repository, and the unindexed ones are queued."""
        text = GetRepositoryOverviewTool(self.all()).call({})
        for repository in self.repositories:
            self.assertIn(f"[{repository.name}]({repository.github_url})", text)
        self.assertIn("not yet", text)
        self.mock_index_task.delay.assert_called_once_with(self.unindexed_repository.name)

    def test_unindexed_repository(self):
        """A repository that is not indexed is an error, and is queued for indexing once."""
        tool = GetRepositoryOverviewTool(self.single(self.unindexed_repository))
        for _ in range(2):
            with self.assertRaisesRegex(SmarterMCPServerToolError, "has not been indexed yet"):
                tool.call({})
        self.mock_index_task.delay.assert_called_once_with(self.unindexed_repository.name)

    # -------------------------------------------------------------------------
    # search_documentation, search_code
    # -------------------------------------------------------------------------
    def test_search_documentation(self):
        """Documentation hits link to the published page and the source."""
        text = SearchDocumentationTool(self.single()).call({"query": "custom domain verification", "limit": 3})
        self.assertIn("results in the documentation of", text)
        self.assertIn("1. **Custom Domains** `docs/source/custom-domains.rst`", text)
        self.assertIn(f"Documentation: {DOCS_URL}custom-domains.html", text)
        self.assertIn("```text", text)

    def test_search_code(self):
        """Code hits show their lines in a fenced block of the file's language, and may be limited to a folder."""
        text = SearchCodeTool(self.single()).call({"query": "lookup_dns_records", "path": "platform/apps"})
        self.assertIn("`platform/apps/domains/verification.py`", text)
        self.assertIn("```python", text)
        self.assertNotIn("Documentation:", text)

    def test_search_without_results(self):
        """A search without results suggests other keywords."""
        text = SearchCodeTool(self.single()).call({"query": "zzzyyyxxx"})
        self.assertIn("No code of", text)

    def test_search_all_repositories(self):
        """A search of all of the repositories names each hit's repository, and notes the unindexed ones."""
        text = SearchCodeTool(self.all()).call({"query": "apply manifest", "limit": 10})
        self.assertIn(f"in {self.code_repository.name}", text)
        self.assertIn(f"still being indexed: {self.unindexed_repository.name}", text)
        named = SearchCodeTool(self.all()).call({"query": "apply", "repository": self.code_repository.name})
        self.assertNotIn(self.docs_repository.name, named)

    def test_search_of_an_unindexed_repository(self):
        """Searching only repositories that are not indexed is an error."""
        with self.assertRaisesRegex(SmarterMCPServerToolError, "has not been indexed yet"):
            SearchCodeTool(self.single(self.unindexed_repository)).call({"query": "apply"})

    # -------------------------------------------------------------------------
    # read_file
    # -------------------------------------------------------------------------
    def test_read_file(self):
        """A file is read with line numbers, a permalink and its published page."""
        text = ReadFileTool(self.single()).call({"path": "/docs/source/custom-domains.rst"})
        self.assertIn(f"{self.docs_repository.name}/docs/source/custom-domains.rst, lines 1-11 of 11", text)
        self.assertIn(f"/blob/{COMMIT_SHA}/docs/source/custom-domains.rst#L1-L11", text)
        self.assertIn(f"Published at {DOCS_URL}custom-domains.html", text)
        self.assertIn(" 1  Custom Domains", text)
        self.assertNotIn("The file continues", text)

    def test_read_file_range(self):
        """A range of lines is read, and the result says where the file continues."""
        text = ReadFileTool(self.single()).call(
            {"path": "platform/apps/domains/verification.py", "start_line": 4, "end_line": 5}
        )
        self.assertIn("lines 4-5 of 12", text)
        self.assertIn("4  def verify_custom_domain", text)
        self.assertIn("call read_file with start_line=6", text)

    def test_read_file_limits(self):
        """At most MAX_READ_LINES lines, and MAX_READ_CHARACTERS characters, are read at once."""
        with mock.patch.object(tools, "MAX_READ_LINES", 2):
            self.assertIn(
                "lines 1-2 of 12", ReadFileTool(self.single()).call({"path": "platform/apps/domains/verification.py"})
            )
        with mock.patch.object(tools, "MAX_READ_CHARACTERS", 40):
            text = ReadFileTool(self.single()).call({"path": "platform/apps/domains/verification.py"})
        self.assertIn("call read_file with start_line=", text)

    def test_read_file_not_found(self):
        """A file that does not exist is an error that suggests the files the LLM may have meant."""
        with self.assertRaisesRegex(SmarterMCPServerToolError, "Did you mean: platform/apps/domains/models.py"):
            ReadFileTool(self.single()).call({"path": "domains/models.py"})
        with self.assertRaisesRegex(SmarterMCPServerToolError, "Did you mean: platform/apps/domains/verification.py"):
            ReadFileTool(self.single()).call({"path": "verification"})
        with self.assertRaisesRegex(SmarterMCPServerToolError, "Use list_files"):
            ReadFileTool(self.single()).call({"path": "nothing/like/this.py"})

    def test_read_file_requires_a_repository(self):
        """The MCP server of all of the repositories needs the repository of the file."""
        with self.assertRaisesRegex(SmarterMCPServerToolError, "repository is required"):
            ReadFileTool(self.all()).call({"path": "README.md"})
        text = ReadFileTool(self.all()).call({"path": "README.md", "repository": self.code_repository.name})
        self.assertIn("Test CLI", text)

    # -------------------------------------------------------------------------
    # list_files
    # -------------------------------------------------------------------------
    def test_list_files(self):
        """A folder lists its folders, with their number of files, then its files."""
        text = ListFilesTool(self.single()).call({})
        self.assertIn("(top level)", text)
        self.assertLess(text.index("- docs/ (3 files)"), text.index("- README.md"))
        text = ListFilesTool(self.single()).call({"path": "platform/apps/domains/"})
        self.assertIn("- models.py (", text)
        self.assertIn(f"/tree/{COMMIT_SHA}/platform/apps/domains", text)

    def test_list_files_limit(self):
        """At most MAX_LIST_ENTRIES entries are listed."""
        with mock.patch.object(tools, "MAX_LIST_ENTRIES", 1):
            text = ListFilesTool(self.single()).call({})
        self.assertIn("more", text)

    def test_list_files_not_a_folder(self):
        """A folder without indexed files is an error."""
        with self.assertRaisesRegex(SmarterMCPServerToolError, "is not a folder"):
            ListFilesTool(self.single()).call({"path": "no/such/folder"})
