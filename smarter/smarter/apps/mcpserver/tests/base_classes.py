"""
Test harness for the mcpserver app.

The tests never contact GitHub. :class:`MCPServerTestBase` replaces The Smarter Project's
repositories with throwaway test repositories, whose names are unique to the test class, so
that their indexes never collide with the real repositories' indexes in the database. It
indexes two of them from ./data/repository-files.yaml, and leaves a third unindexed. The
Celery task that indexes a repository is replaced for every test.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import io
import os
import tarfile
from unittest import mock

from cache_results import lazy_cache

from smarter.apps.mcpserver.indexer import ArchiveFile, file_kind, store_files
from smarter.apps.mcpserver.models import RepositoryIndex
from smarter.apps.mcpserver.repositories import ProjectRepository
from smarter.apps.mcpserver.tools import queue_indexing_key
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.typing import SmarterDictType
from smarter.lib.unittest.base_classes import SmarterTestBase

HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.join(HERE, "data")

COMMIT_SHA = "0123456789abcdef0123456789abcdef01234567"
NEW_COMMIT_SHA = "fedcba9876543210fedcba9876543210fedcba98"
DOCS_URL = "https://docs.example.com/en/latest/"
REPOSITORIES_PATCH = "smarter.apps.mcpserver.repositories.SMARTER_PROJECT_REPOSITORIES"
INDEX_TASK_PATCH = "smarter.apps.mcpserver.tasks.index_repository"


def repository_files() -> SmarterDictType:
    """Return the test repositories' files, from ./data/repository-files.yaml."""
    return get_readonly_yaml_file(os.path.join(DATA_PATH, "repository-files.yaml"))


def archive_files(files: list[SmarterDictType]) -> list[ArchiveFile]:
    """Return test files as the indexer's :class:`ArchiveFile`, without reading an archive."""
    result = []
    for file in files:
        content = file["content"]
        kind = file_kind(file["path"])
        assert kind is not None, file["path"]  # nosec B101: a test fixture
        title = content.splitlines()[0].lstrip("# ") if kind == "documentation" else ""
        result.append(
            ArchiveFile(
                path=file["path"],
                kind=kind,
                title=title,
                content=content,
                size=len(content.encode()),
                line_count=content.count("\n"),
            )
        )
    return result


def build_archive(repository_name: str, commit_sha: str, files: dict[str, bytes]) -> bytes:
    """
    Return a gzipped tar archive, like GitHub's codeload service returns.

    :param repository_name: The repository's name, for the archive's top-level folder.
    :param commit_sha: The commit, for the archive's top-level folder.
    :param files: The files' content, by path.
    :returns: The archive.
    """
    buffer = io.BytesIO()
    root = f"{repository_name}-{commit_sha}"
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        folder = tarfile.TarInfo(root)
        folder.type = tarfile.DIRTYPE
        tar.addfile(folder)
        for path, content in files.items():
            info = tarfile.TarInfo(f"{root}/{path}")
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


class MCPServerTestBase(SmarterTestBase):
    """
    Base class for the mcpserver app's tests.

    - ``docs_repository``: a repository with published documentation, indexed at :data:`COMMIT_SHA`.
    - ``code_repository``: a repository without published documentation, indexed at :data:`COMMIT_SHA`.
    - ``unindexed_repository``: a repository that is not indexed.

    ``mock_index_task`` replaces the Celery task that indexes a repository.
    """

    docs_repository: ProjectRepository
    code_repository: ProjectRepository
    unindexed_repository: ProjectRepository
    repositories: tuple[ProjectRepository, ...]
    docs_index: RepositoryIndex
    code_index: RepositoryIndex

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        suffix = cls.hash_suffix.lower()
        cls.docs_repository = ProjectRepository(
            name=f"test-mcpserver-docs-{suffix}",
            title="the test platform",
            description="The test platform, and its documentation.",
            docs_root="docs/source",
            docs_url=DOCS_URL,
        )
        cls.code_repository = ProjectRepository(
            name=f"test-mcpserver-code-{suffix}", title="the test cli", description="The test command-line interface."
        )
        cls.unindexed_repository = ProjectRepository(
            name=f"test-mcpserver-unindexed-{suffix}", title="the test sdk", description="A test sdk."
        )
        cls.repositories = (cls.docs_repository, cls.code_repository, cls.unindexed_repository)
        cls.repositories_patcher = mock.patch(REPOSITORIES_PATCH, cls.repositories)
        cls.repositories_patcher.start()
        files = repository_files()
        cls.docs_index = cls.build_index(cls.docs_repository, files["docs"])
        cls.code_index = cls.build_index(cls.code_repository, files["code"])

    @classmethod
    def tearDownClass(cls):
        try:
            RepositoryIndex.objects.filter(repository__in=[repository.name for repository in cls.repositories]).delete()
        finally:
            cls.repositories_patcher.stop()
            super().tearDownClass()

    @classmethod
    def build_index(cls, repository: ProjectRepository, files: list[SmarterDictType]) -> RepositoryIndex:
        """Index a test repository's files, at :data:`COMMIT_SHA`."""
        index, _ = RepositoryIndex.objects.get_or_create(repository=repository.name)
        return store_files(index, COMMIT_SHA, archive_files(files))

    def setUp(self):
        super().setUp()
        patcher = mock.patch(INDEX_TASK_PATCH)
        self.mock_index_task = patcher.start()
        self.addCleanup(patcher.stop)
        for repository in self.repositories:
            lazy_cache.delete(queue_indexing_key(repository.name))
