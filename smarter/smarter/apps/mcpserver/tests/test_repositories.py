"""Tests for smarter.apps.mcpserver.repositories."""

from smarter.apps.mcpserver.repositories import (
    SMARTER_PROJECT_DOCS_LATEST_URL,
    SMARTER_PROJECT_REPOSITORIES,
    ProjectRepository,
    get_repository,
    project_repositories,
    repository_names,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

SHA = "0123456789abcdef0123456789abcdef01234567"


class TestProjectRepositories(SmarterTestBase):
    """Test The Smarter Project's repositories, and their urls."""

    def test_registry(self):
        """Every public repository of The Smarter Project is registered once, on main."""
        names = repository_names()
        self.assertEqual(len(names), len(set(names)))
        for name in (
            "smarter",
            "smarter-cli",
            "smarter-python",
            "smarter-nodejs",
            "smarter-golang",
            "smarter-vscode-yaml",
            "smarter-infrastructure",
            "smarter-chat",
            "smarter-deploy",
        ):
            with self.subTest(name=name):
                repository = get_repository(name)
                self.assertIsNotNone(repository)
                self.assertEqual(repository.owner, "smarter-sh")
                self.assertEqual(repository.ref, "main")
                self.assertTrue(repository.title and repository.description)
        self.assertEqual(project_repositories(), SMARTER_PROJECT_REPOSITORIES)
        self.assertIsNone(get_repository("not-a-repository"))

    def test_only_smarter_publishes_documentation(self):
        """The smarter repository's docs/source is the published documentation."""
        smarter = get_repository("smarter")
        self.assertEqual(smarter.docs_root, "docs/source")
        self.assertEqual(smarter.docs_url, SMARTER_PROJECT_DOCS_LATEST_URL)
        self.assertEqual(SMARTER_PROJECT_DOCS_LATEST_URL, "https://docs.smarter.sh/en/latest/")
        self.assertIsNone(get_repository("smarter-cli").docs_url)

    def test_github_urls(self):
        """The GitHub, api and archive urls of a repository."""
        repository = get_repository("smarter-cli")
        self.assertEqual(repository.full_name, "smarter-sh/smarter-cli")
        self.assertEqual(repository.github_url, "https://github.com/smarter-sh/smarter-cli")
        self.assertEqual(repository.commit_api_url, "https://api.github.com/repos/smarter-sh/smarter-cli/commits/main")
        self.assertEqual(
            repository.archive_url(SHA), f"https://codeload.github.com/smarter-sh/smarter-cli/tar.gz/{SHA}"
        )

    def test_file_url(self):
        """A file's url names the commit, or the branch, and highlights its lines."""
        repository = get_repository("smarter-cli")
        base = "https://github.com/smarter-sh/smarter-cli/blob"
        self.assertEqual(repository.file_url(SHA, "cmd/apply.go"), f"{base}/{SHA}/cmd/apply.go")
        self.assertEqual(repository.file_url(None, "cmd/apply.go"), f"{base}/main/cmd/apply.go")
        self.assertEqual(repository.file_url(SHA, "a.go", 10), f"{base}/{SHA}/a.go#L10")
        self.assertEqual(repository.file_url(SHA, "a.go", 10, 10), f"{base}/{SHA}/a.go#L10")
        self.assertEqual(repository.file_url(SHA, "a.go", 10, 20), f"{base}/{SHA}/a.go#L10-L20")

    def test_documentation_url(self):
        """A Sphinx source file under docs_root is published as an html page."""
        smarter = get_repository("smarter")
        self.assertEqual(
            smarter.documentation_url("docs/source/smarter-resources/smarter-mcpclient.rst"),
            "https://docs.smarter.sh/en/latest/smarter-resources/smarter-mcpclient.html",
        )
        self.assertEqual(
            smarter.documentation_url("docs/source/guides/intro.md"),
            "https://docs.smarter.sh/en/latest/guides/intro.html",
        )
        self.assertIsNone(smarter.documentation_url("docs/source/conf.py"))
        self.assertIsNone(smarter.documentation_url("README.md"))
        self.assertIsNone(get_repository("smarter-cli").documentation_url("docs/source/index.rst"))

    def test_frozen(self):
        """A repository is immutable, and has no undeclared fields."""
        repository = get_repository("smarter-cli")
        with self.assertRaises(Exception):
            repository.name = "other"  # type: ignore[misc]
        with self.assertRaises(Exception):
            ProjectRepository(name="x", title="x", description="x", unknown="x")  # type: ignore[call-arg]
