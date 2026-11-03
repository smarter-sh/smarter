"""Tests for smarter.apps.mcpserver.services.reading, called directly, without the tools that format it."""

from smarter.apps.mcpserver.exceptions import (
    SmarterMCPServerNotFoundError,
    SmarterMCPServerServiceError,
)
from smarter.apps.mcpserver.services.reading import (
    FileLines,
    FolderListing,
    PostLines,
    RepositoryOverview,
    list_files,
    read_blog_post,
    read_file,
    read_lines,
    repositories_state,
    repository_overview,
)

from .base_classes import BLOG_URL, COMMIT_SHA, DOCS_URL, MCPServerTestBase

SECRETS_POST = "2026/10/20/keeping-secrets-out-of-the-logs"


class TestReadLines(MCPServerTestBase):
    """Test read_lines, which needs no database."""

    def test_reads_a_range_with_numbers(self):
        """The lines are numbered, right-aligned to the widest number."""
        lines = read_lines("a\nb\nc\nd", 2, 3)
        self.assertEqual((lines.start, lines.end, lines.total), (2, 3, 4))
        self.assertEqual(lines.text, "2  b\n3  c")
        self.assertFalse(lines.is_complete)

    def test_a_start_after_the_end_reads_the_last_line(self):
        """A start beyond the file reads its last line, rather than nothing."""
        lines = read_lines("a\nb", 9, None)
        self.assertEqual((lines.start, lines.end), (2, 2))
        self.assertTrue(lines.is_complete)


class TestReadingService(MCPServerTestBase):
    """Test the reading service on the test index."""

    def test_read_file(self):
        """A file's lines come with its GitHub url and its published page."""
        file_lines = read_file(self.docs_repository, "/docs/source/custom-domains.rst")
        self.assertIsInstance(file_lines, FileLines)
        self.assertEqual(file_lines.path, "docs/source/custom-domains.rst")
        self.assertEqual(file_lines.repository, self.docs_repository.name)
        self.assertIn(f"/blob/{COMMIT_SHA}/docs/source/custom-domains.rst#L1-L11", file_lines.github_url)
        self.assertEqual(file_lines.documentation_url, f"{DOCS_URL}custom-domains.html")
        self.assertTrue(file_lines.lines.is_complete)

    def test_read_file_not_found_suggests_files(self):
        """A file that does not exist names the files that the caller may have meant, and no tool."""
        with self.assertRaises(SmarterMCPServerNotFoundError) as context:
            read_file(self.docs_repository, "domains/models.py")
        self.assertEqual(context.exception.suggestions, ["platform/apps/domains/models.py"])
        self.assertIn("Did you mean: platform/apps/domains/models.py?", context.exception.message)
        with self.assertRaises(SmarterMCPServerNotFoundError) as context:
            read_file(self.docs_repository, "nothing/like/this.py")
        self.assertEqual(context.exception.suggestions, [])
        self.assertNotIn("list_files", context.exception.message, "a service names no tool")

    def test_unindexed_repository(self):
        """A repository that is not indexed is a service error, and is queued for indexing."""
        with self.assertRaisesRegex(SmarterMCPServerServiceError, "has not been indexed yet"):
            read_file(self.unindexed_repository, "README.md")
        self.mock_index_task.delay.assert_called_once_with(self.unindexed_repository.name)

    def test_list_files(self):
        """A folder's entries are its folders, with their files, then its files, with their sizes."""
        listing = list_files(self.docs_repository)
        self.assertIsInstance(listing, FolderListing)
        self.assertEqual(listing.folder, "")
        folders = [entry for entry in listing.entries if entry.is_folder]
        files = [entry for entry in listing.entries if not entry.is_folder]
        self.assertIn("docs", [entry.name for entry in folders])
        self.assertIn("README.md", [entry.name for entry in files])
        self.assertLess(listing.entries.index(folders[-1]), listing.entries.index(files[0]))
        self.assertEqual(listing.hidden, 0)

    def test_list_files_of_a_missing_folder(self):
        """A folder without indexed files is not found, with nothing to suggest."""
        with self.assertRaises(SmarterMCPServerNotFoundError) as context:
            list_files(self.docs_repository, "no/such/folder/")
        self.assertEqual(context.exception.suggestions, [])
        self.assertIn("no/such/folder is not a folder of", context.exception.message)

    def test_repository_overview(self):
        """An overview counts the files, lists the top level, and has the README."""
        overview = repository_overview(self.docs_repository)
        self.assertIsInstance(overview, RepositoryOverview)
        self.assertEqual(overview.commit_sha, COMMIT_SHA)
        self.assertEqual(overview.documentation_files + overview.code_files, overview.file_count)
        self.assertEqual(overview.readme_path, "README.md")
        self.assertIn("governed AI applications", overview.readme)
        self.assertFalse(overview.readme_truncated)

    def test_repositories_state(self):
        """Each repository says whether it is indexed, in order, and the unindexed ones are queued."""
        states = repositories_state(self.repositories)
        self.assertEqual([state.repository.name for state in states], [r.name for r in self.repositories])
        by_name = {state.repository.name: state for state in states}
        self.assertTrue(by_name[self.docs_repository.name].is_indexed)
        self.assertEqual(by_name[self.docs_repository.name].commit_sha, COMMIT_SHA)
        self.assertFalse(by_name[self.unindexed_repository.name].is_indexed)
        self.mock_index_task.delay.assert_called_once_with(self.unindexed_repository.name)

    def test_read_blog_post(self):
        """A post is read by its path or its url."""
        post = read_blog_post(f"{BLOG_URL}/{SECRETS_POST}/", start_line=1, end_line=2)
        self.assertIsInstance(post, PostLines)
        self.assertEqual(post.path, SECRETS_POST)
        self.assertEqual(post.url, f"{BLOG_URL}/{SECRETS_POST}/")
        self.assertEqual((post.lines.start, post.lines.end), (1, 2))

    def test_read_blog_post_not_found(self):
        """A post that does not exist suggests the posts with the same slug."""
        with self.assertRaises(SmarterMCPServerNotFoundError) as context:
            read_blog_post("2025/01/01/keeping-secrets")
        self.assertEqual(context.exception.suggestions, [SECRETS_POST])
