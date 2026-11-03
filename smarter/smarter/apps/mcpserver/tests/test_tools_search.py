"""Tests for smarter.apps.mcpserver.protocol.tools.search, through the search service that it calls."""

from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.models import RepositoryIndex, RepositoryIndexStatus
from smarter.apps.mcpserver.protocol.tools.reading import ReadBlogPostTool
from smarter.apps.mcpserver.protocol.tools.search import (
    SearchBlogTool,
    SearchCodeTool,
    SearchDocumentationTool,
)

from .base_classes import BLOG_URL, DOCS_URL, MCPServerTestBase

SECRETS_POST = "2026/10/20/keeping-secrets-out-of-the-logs"


class TestSearchTools(MCPServerTestBase):
    """Test search_documentation, search_code and search_blog, on the public endpoint of one repository, and of every repository."""

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

    def test_blog_tools_are_project_wide(self):
        """Only the public endpoint of every repository serves the blog's tools."""
        self.assertTrue(SearchBlogTool.serves(self.all()))
        self.assertFalse(SearchBlogTool.serves(self.single()))
        self.assertFalse(ReadBlogPostTool.serves(self.single()))
        self.assertTrue(SearchCodeTool.serves(self.single()))

    def test_search_blog(self):
        """Blog hits link to the post, and show a passage of it."""
        text = SearchBlogTool(self.all()).call({"query": "leaked passwords logs", "repository": "ignored"})
        self.assertIn("posts of the blog", text)
        self.assertIn(f"1. **Keeping Secrets Out of the Logs – a Review** `{SECRETS_POST}`", text)
        self.assertIn(f"Post: {BLOG_URL}/{SECRETS_POST}/", text)
        self.assertIn("leaked credentials", text)

    def test_search_blog_without_results(self):
        """A search of the blog without results suggests search_documentation."""
        self.assertIn("No post of the blog", SearchBlogTool(self.all()).call({"query": "zzzyyyxxx"}))

    def test_unindexed_blog(self):
        """A blog that is not indexed is an error, and is queued for indexing once."""
        RepositoryIndex.objects.filter(pk=self.blog_index.pk).update(status=RepositoryIndexStatus.PENDING)
        self.addCleanup(
            RepositoryIndex.objects.filter(pk=self.blog_index.pk).update, status=RepositoryIndexStatus.READY
        )
        with self.assertRaisesRegex(SmarterMCPServerToolError, "has not been indexed yet"):
            SearchBlogTool(self.all()).call({"query": "logs"})
        with self.assertRaisesRegex(SmarterMCPServerToolError, "has not been indexed yet"):
            ReadBlogPostTool(self.all()).call({"path": SECRETS_POST})
        self.mock_index_blog_task.delay.assert_called_once_with()
        self.mock_index_task.delay.assert_not_called()
