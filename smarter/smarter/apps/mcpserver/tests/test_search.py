"""Tests for smarter.apps.mcpserver.services.search."""

from smarter.apps.mcpserver.exceptions import SmarterMCPServerServiceError
from smarter.apps.mcpserver.models import RepositoryFileKind
from smarter.apps.mcpserver.services.search import (
    MAX_TERMS,
    matching_lines,
    query_terms,
    search_blog,
    search_code,
    search_documentation,
    search_files,
)

from .base_classes import COMMIT_SHA, DOCS_URL, MCPServerTestBase


class TestSearch(MCPServerTestBase):
    """Test search_files(), on the test repositories."""

    def test_query_terms(self):
        """Queries are split into lowercase terms, phrases and identifiers, without common words."""
        self.assertEqual(
            query_terms('How does "Custom Domain" verification work?'), ["custom domain", "verification", "work"]
        )
        self.assertEqual(
            query_terms("smarter_settings.environment_platform_domain smarter/apps/llmclient"),
            ["smarter_settings.environment_platform_domain", "smarter/apps/llmclient"],
        )
        self.assertEqual(query_terms("the a of"), [])
        self.assertEqual(query_terms(""), [])
        self.assertEqual(query_terms("apply APPLY Apply"), ["apply"])
        self.assertEqual(len(query_terms(" ".join(f"word{i}" for i in range(20)))), MAX_TERMS)

    def test_documentation_search(self):
        """The best documentation comes first, with a passage and links to the page and the source."""
        hits = search_files([self.docs_repository], "custom domain verification", kind=RepositoryFileKind.DOCUMENTATION)
        self.assertEqual(hits[0].path, "docs/source/custom-domains.rst")
        self.assertEqual(hits[0].title, "Custom Domains")
        self.assertEqual(hits[0].documentation_url, f"{DOCS_URL}custom-domains.html")
        self.assertIn(f"/blob/{COMMIT_SHA}/docs/source/custom-domains.rst#L", hits[0].url)
        self.assertTrue(any("verification checks" in line.text for line in hits[0].lines))
        self.assertTrue(all(hit.kind == RepositoryFileKind.DOCUMENTATION for hit in hits))
        self.assertEqual(sorted(hits, key=lambda hit: -hit.score), hits)

    def test_code_search(self):
        """Code hits show the lines that contain the terms, with their numbers."""
        hits = search_files([self.docs_repository], "verify_custom_domain", kind=RepositoryFileKind.CODE)
        self.assertEqual(hits[0].path, "platform/apps/domains/verification.py")
        self.assertIsNone(hits[0].documentation_url)
        numbers = [line.number for line in hits[0].lines]
        self.assertEqual(numbers, sorted(numbers))
        self.assertIn("def verify_custom_domain", " ".join(line.text for line in hits[0].lines))

    def test_path_matches_count(self):
        """A term in a file's path ranks the file higher."""
        hits = search_files([self.docs_repository], "settings", kind=RepositoryFileKind.CODE)
        self.assertEqual(hits[0].path, "platform/settings.py")

    def test_path_filter(self):
        """Only files under the path are searched."""
        hits = search_files([self.docs_repository], "custom domain", path="/platform/apps/")
        self.assertTrue(hits)
        self.assertTrue(all(hit.path.startswith("platform/apps/") for hit in hits))

    def test_several_repositories(self):
        """Every repository is searched, and its hits link to its own files."""
        hits = search_files([self.docs_repository, self.code_repository], "apply manifest", limit=20)
        repositories = {hit.repository for hit in hits}
        self.assertEqual(repositories, {self.docs_repository.name, self.code_repository.name})
        for hit in hits:
            self.assertIn(f"/smarter-sh/{hit.repository}/blob/", hit.url)

    def test_limit(self):
        """At most limit hits are returned."""
        self.assertEqual(len(search_files([self.docs_repository], "custom domain", limit=1)), 1)

    def test_no_results(self):
        """A query that matches nothing, has no terms, or names no repository, returns nothing."""
        self.assertEqual(search_files([self.docs_repository], "zzzyyyxxx"), [])
        self.assertEqual(search_files([self.docs_repository], "the of"), [])
        self.assertEqual(search_files([], "custom domain"), [])
        self.assertEqual(search_files([self.unindexed_repository], "custom domain"), [])

    def test_matching_lines(self):
        """Matching lines are clipped.

        A file without a match shows its first lines.
        """
        long_line = "match " + "x" * 500
        lines = matching_lines(f"{long_line}\nother\n", ["match"], RepositoryFileKind.CODE)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].text.endswith("…"))
        self.assertEqual([line.number for line in matching_lines("a\nb\n", ["zzz"], RepositoryFileKind.CODE)], [1, 2])
        passage = matching_lines(
            "\n".join(f"line {i}" for i in range(30)) + "\nthe match\n", ["match"], "documentation"
        )
        self.assertEqual(passage[-1].text, "the match")
        self.assertEqual(passage[0].number, 29)


class TestSearchServices(MCPServerTestBase):
    """Test search_documentation, search_code and search_blog, which search only the indexes that are ready."""

    def test_search_documentation(self):
        """Only documentation is searched, and the repositories that are not indexed are named."""
        results = search_documentation(self.repositories, "custom domain verification", limit=5)
        self.assertTrue(results.hits)
        for hit in results.hits:
            self.assertEqual(hit.kind, RepositoryFileKind.DOCUMENTATION)
        self.assertEqual(results.not_indexed, [self.unindexed_repository.name])
        self.mock_index_task.delay.assert_called_once_with(self.unindexed_repository.name)

    def test_search_code_under_a_folder(self):
        """Only code under the folder is searched."""
        results = search_code([self.docs_repository], "lookup_dns_records", limit=5, path="platform/apps")
        self.assertTrue(results.hits)
        for hit in results.hits:
            self.assertEqual(hit.kind, RepositoryFileKind.CODE)
            self.assertTrue(hit.path.startswith("platform/apps/"))
        self.assertEqual(results.not_indexed, [])

    def test_nothing_indexed(self):
        """A search of repositories that are none of them indexed is a service error."""
        with self.assertRaisesRegex(SmarterMCPServerServiceError, "has not been indexed yet"):
            search_code([self.unindexed_repository], "apply", limit=5)

    def test_search_blog(self):
        """The blog's posts are searched."""
        hits = search_blog("leaked passwords logs", limit=3)
        self.assertTrue(hits)
        self.assertEqual(hits[0].repository, self.blog.name)
