"""Tests for smarter.apps.mcpserver.services.indexing.indexes: which indexes are ready, and the queuing of the others."""

from smarter.apps.mcpserver.exceptions import SmarterMCPServerServiceError
from smarter.apps.mcpserver.models import RepositoryIndex, RepositoryIndexStatus
from smarter.apps.mcpserver.services.indexing.indexes import (
    queue_indexing,
    ready_indexes,
    require_blog_index,
    require_index,
)

from .base_classes import MCPServerTestBase


class TestIndexes(MCPServerTestBase):
    """Test the indexes service on the test index."""

    def test_ready_indexes(self):
        """Only the ready indexes are returned, and the others are queued for indexing."""
        ready = ready_indexes(self.repositories)
        self.assertIn(self.docs_repository.name, ready)
        self.assertNotIn(self.unindexed_repository.name, ready)
        self.mock_index_task.delay.assert_called_once_with(self.unindexed_repository.name)

    def test_queue_indexing_once(self):
        """A repository is queued only once while its key is in the cache."""
        queue_indexing(self.unindexed_repository)
        queue_indexing(self.unindexed_repository)
        self.mock_index_task.delay.assert_called_once_with(self.unindexed_repository.name)

    def test_require_index(self):
        """A ready repository's index is returned, and one that is not ready is a service error."""
        index = require_index(self.docs_repository)
        self.assertEqual(index.repository, self.docs_repository.name)
        with self.assertRaisesRegex(SmarterMCPServerServiceError, "has not been indexed yet"):
            require_index(self.unindexed_repository)

    def test_require_blog_index(self):
        """The blog's index is returned, and a blog that is not ready is queued for indexing."""
        self.assertEqual(require_blog_index(self.blog).repository, self.blog.name)
        RepositoryIndex.objects.filter(pk=self.blog_index.pk).update(status=RepositoryIndexStatus.PENDING)
        self.addCleanup(
            RepositoryIndex.objects.filter(pk=self.blog_index.pk).update, status=RepositoryIndexStatus.READY
        )
        with self.assertRaisesRegex(SmarterMCPServerServiceError, "The blog, .*, has not been indexed yet"):
            require_blog_index(self.blog)
        self.mock_index_blog_task.delay.assert_called_once_with()
