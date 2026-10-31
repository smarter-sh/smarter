"""Tests for smarter.apps.mcpserver.caching."""

from unittest import mock

from smarter.apps.mcpserver import caching
from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.index.tools import SearchCodeTool, SearchDocumentationTool
from smarter.apps.mcpserver.protocol.tools import SmarterProjectScope
from smarter.apps.mcpserver.receivers import handle_mcpserver_repository_indexed

from .base_classes import MCPServerTestBase


class TestCaching(MCPServerTestBase):
    """Test that the MCP server's tool results are cached until an index changes."""

    def scope(self) -> SmarterProjectScope:
        return SmarterProjectScope(repository=self.code_repository, repositories=(self.code_repository,))

    def test_a_result_is_cached_by_its_arguments(self):
        """The same call runs the tool once, and other arguments run it again."""
        tool = SearchCodeTool(self.scope())
        with mock.patch.object(SearchCodeTool, "run", autospec=True, side_effect=SearchCodeTool.run) as run:
            first = tool.call({"query": "apply manifest"})
            second = SearchCodeTool(self.scope()).call({"query": "apply manifest"})
            tool.call({"query": "lookup_dns_records"})
        self.assertEqual(first, second)
        self.assertEqual(run.call_count, 2)

    def test_tools_and_scopes_have_their_own_results(self):
        """Two tools with the same arguments, or one tool of two scopes, are cached separately."""
        everything = SmarterProjectScope(repository=None, repositories=self.repositories)
        with (
            mock.patch.object(SearchCodeTool, "run", autospec=True, side_effect=SearchCodeTool.run) as code,
            mock.patch.object(
                SearchDocumentationTool, "run", autospec=True, side_effect=SearchDocumentationTool.run
            ) as docs,
        ):
            SearchCodeTool(self.scope()).call({"query": "apply"})
            SearchDocumentationTool(self.scope()).call({"query": "apply"})
            SearchCodeTool(everything).call({"query": "apply"})
        self.assertEqual((code.call_count, docs.call_count), (2, 1))

    def test_a_new_index_generation_invalidates_the_results(self):
        """An index that changes makes every cached result stale."""
        tool = SearchCodeTool(self.scope())
        with mock.patch.object(SearchCodeTool, "run", autospec=True, side_effect=SearchCodeTool.run) as run:
            tool.call({"query": "apply manifest"})
            generation = caching.index_generation()
            handle_mcpserver_repository_indexed(sender=None, index=self.code_index)
            self.assertGreater(caching.index_generation(), generation)
            tool.call({"query": "apply manifest"})
        self.assertEqual(run.call_count, 2)

    def test_errors_are_not_cached(self):
        """A tool that fails runs again on the next call."""
        tool = SearchCodeTool(self.scope())
        with mock.patch.object(SearchCodeTool, "run", side_effect=SmarterMCPServerToolError("broken")) as run:
            for _ in range(2):
                with self.assertRaisesRegex(SmarterMCPServerToolError, "broken"):
                    tool.call({"query": "apply"})
        self.assertEqual(run.call_count, 2)

    def test_index_generation_without_a_cached_value(self):
        """Without a generation in the cache, the generation is 0."""
        with mock.patch.object(caching.lazy_cache, "get", return_value=None):
            self.assertEqual(caching.index_generation(), 0)
