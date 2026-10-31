"""Tests for smarter.apps.mcpserver.index.tools."""

from unittest import mock

from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.index import tools as index_tools
from smarter.apps.mcpserver.index.tools import (
    GetRepositoryOverviewTool,
    ListFilesTool,
    ReadBlogPostTool,
    ReadFileTool,
    SearchBlogTool,
    SearchCodeTool,
    SearchDocumentationTool,
)
from smarter.apps.mcpserver.models import RepositoryIndex, RepositoryIndexStatus

from .base_classes import BLOG_URL, COMMIT_SHA, DOCS_URL, MCPServerTestBase

SECRETS_POST = "2026/10/20/keeping-secrets-out-of-the-logs"


class TestIndexTools(MCPServerTestBase):
    """Test the tools that answer from the index, on the MCP server of one repository, and of all of them."""

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
        with mock.patch.object(index_tools, "MAX_README_CHARACTERS", 10):
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
        with mock.patch.object(index_tools, "MAX_READ_LINES", 2):
            self.assertIn(
                "lines 1-2 of 12", ReadFileTool(self.single()).call({"path": "platform/apps/domains/verification.py"})
            )
        with mock.patch.object(index_tools, "MAX_READ_CHARACTERS", 40):
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
        with mock.patch.object(index_tools, "MAX_LIST_ENTRIES", 1):
            text = ListFilesTool(self.single()).call({})
        self.assertIn("more", text)

    def test_list_files_not_a_folder(self):
        """A folder without indexed files is an error."""
        with self.assertRaisesRegex(SmarterMCPServerToolError, "is not a folder"):
            ListFilesTool(self.single()).call({"path": "no/such/folder"})

    # -------------------------------------------------------------------------
    # search_blog, read_blog_post
    # -------------------------------------------------------------------------
    def test_blog_tools_are_project_wide(self):
        """Only the MCP server of all of the repositories serves the blog's tools."""
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

    def test_overview_mentions_the_blog(self):
        """The overview of all of the repositories names the blog's search tool."""
        self.assertIn(
            f"The blog, {BLOG_URL}, is searched with search_blog", GetRepositoryOverviewTool(self.all()).call({})
        )

    def test_read_blog_post(self):
        """A post is read by its path or its url, with line numbers."""
        for path in (SECRETS_POST, f"{BLOG_URL}/{SECRETS_POST}/", f"/{SECRETS_POST}/#how"):
            with self.subTest(path=path):
                text = ReadBlogPostTool(self.all()).call({"path": path})
                self.assertIn(f"{BLOG_URL}/{SECRETS_POST}/, lines 1-", text)
                self.assertIn("1  # Keeping Secrets Out of the Logs", text)
                self.assertIn("Published 2026-10-20, updated 2026-10-22", text)
                self.assertNotIn("The post continues", text)

    def test_read_blog_post_range(self):
        """A range of a post's lines is read, and the result says where it continues."""
        text = ReadBlogPostTool(self.all()).call({"path": SECRETS_POST, "start_line": 1, "end_line": 2})
        self.assertIn("lines 1-2 of", text)
        self.assertIn("call read_blog_post with start_line=3", text)

    def test_read_blog_post_not_found(self):
        """A post that does not exist is an error that suggests the posts the LLM may have meant."""
        with self.assertRaisesRegex(SmarterMCPServerToolError, f"Did you mean: {SECRETS_POST}"):
            ReadBlogPostTool(self.all()).call({"path": "2025/01/01/keeping-secrets"})
        with self.assertRaisesRegex(SmarterMCPServerToolError, "Use search_blog"):
            ReadBlogPostTool(self.all()).call({"path": "no-such-post"})

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
