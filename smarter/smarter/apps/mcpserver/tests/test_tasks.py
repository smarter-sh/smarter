"""Tests for smarter.apps.mcpserver.tasks."""

from unittest import mock

from smarter.apps.mcpserver.models import RepositoryIndex, RepositoryIndexStatus

# imported before MCPServerTestBase replaces index_repository in the tasks module, for each test.
from smarter.apps.mcpserver.tasks import index_repositories
from smarter.apps.mcpserver.tasks import index_repository as index_repository_task

from .base_classes import COMMIT_SHA, MCPServerTestBase

INDEXER_PATCH = "smarter.apps.mcpserver.tasks.indexer.index_repository"


class TestTasks(MCPServerTestBase):
    """Test the Celery tasks, called synchronously."""

    def test_index_repository(self):
        """The task indexes the repository, and returns its status."""
        index = RepositoryIndex(repository="smarter-cli", status=RepositoryIndexStatus.READY, commit_sha=COMMIT_SHA)
        with mock.patch(INDEXER_PATCH, return_value=index) as index_repository:
            self.assertEqual(index_repository_task("smarter-cli", force=True), "ready")
        index_repository.assert_called_once_with("smarter-cli", force=True)

    def test_index_repositories(self):
        """Every repository is queued."""
        self.assertEqual(index_repositories(force=True), len(self.repositories))
        self.assertEqual(self.mock_index_task.delay.call_count, len(self.repositories))
        self.mock_index_task.delay.assert_any_call(self.code_repository.name, force=True)
