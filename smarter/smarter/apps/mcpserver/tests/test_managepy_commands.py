"""Tests for manage.py index_smarter_project."""

import io
from unittest import mock

from django.core.management import call_command

from smarter.apps.mcpserver.models import RepositoryIndex, RepositoryIndexStatus

from .base_classes import COMMIT_SHA, MCPServerTestBase

COMMAND = "smarter.apps.mcpserver.management.commands.index_smarter_project"


class TestIndexSmarterProjectCommand(MCPServerTestBase):
    """Test manage.py index_smarter_project.

    The indexer and the Celery tasks are replaced.
    """

    def run_command(self, *args) -> str:
        output = io.StringIO()
        call_command("index_smarter_project", *args, stdout=output)
        return output.getvalue()

    def fake_index(self, name, force=False):
        if name == self.unindexed_repository.name:
            return RepositoryIndex(repository=name, status=RepositoryIndexStatus.FAILED, error="GitHub is down")
        return RepositoryIndex(repository=name, status=RepositoryIndexStatus.READY, commit_sha=COMMIT_SHA, file_count=3)

    def fake_blog_index(self, force=False):
        return RepositoryIndex(repository=self.blog.name, status=RepositoryIndexStatus.READY, file_count=2)

    def test_index_every_repository(self):
        """Every repository, and the blog, is indexed, and the failures are reported."""
        with (
            mock.patch(f"{COMMAND}.index_repository", side_effect=self.fake_index) as index_repository,
            mock.patch(f"{COMMAND}.index_blog", side_effect=self.fake_blog_index) as index_blog,
        ):
            output = self.run_command()
        self.assertEqual(index_repository.call_count, len(self.repositories))
        index_blog.assert_called_once_with(force=False)
        self.assertIn(f"{self.blog.name}: ready, 2 posts.", output)
        self.assertIn(f"{self.docs_repository.name}: ready at {COMMIT_SHA}, 3 files.", output)
        self.assertIn(f"{self.unindexed_repository.name}: failed, GitHub is down", output)
        self.assertIn(f"Could not be indexed: {self.unindexed_repository.name}.", output)

    def test_index_one_repository(self):
        """--repository and --force index one repository again, and not the blog."""
        with (
            mock.patch(f"{COMMAND}.index_repository", side_effect=self.fake_index) as index_repository,
            mock.patch(f"{COMMAND}.index_blog") as index_blog,
        ):
            output = self.run_command("--repository", self.code_repository.name, "--force")
        index_repository.assert_called_once_with(self.code_repository.name, force=True)
        index_blog.assert_not_called()
        self.assertNotIn("Could not be indexed", output)

    def test_index_the_blog(self):
        """--blog indexes only the blog, and a failure is reported."""
        failed = RepositoryIndex(repository=self.blog.name, status=RepositoryIndexStatus.FAILED, error="HTTP 503")
        with (
            mock.patch(f"{COMMAND}.index_repository") as index_repository,
            mock.patch(f"{COMMAND}.index_blog", return_value=failed) as index_blog,
        ):
            output = self.run_command("--blog", "--force")
        index_repository.assert_not_called()
        index_blog.assert_called_once_with(force=True)
        self.assertIn(f"{self.blog.name}: failed, HTTP 503", output)
        self.assertIn(f"Could not be indexed: {self.blog.name}.", output)

    def test_unknown_repository(self):
        """Only The Smarter Project's repositories may be named."""
        with self.assertRaises(Exception):
            self.run_command("--repository", "not-a-repository")

    def test_queue(self):
        """--queue queues the indexing for the Celery worker."""
        with mock.patch(f"{COMMAND}.index_repositories") as index_repositories:
            output = self.run_command("--queue")
        index_repositories.delay.assert_called_once_with(force=False)
        self.assertIn("Queued the indexing of", output)
        with mock.patch(f"{COMMAND}.index_repository_task") as index_repository_task:
            self.run_command("--queue", "--repository", self.code_repository.name)
        index_repository_task.delay.assert_called_once_with(self.code_repository.name, force=False)
        with (
            mock.patch(f"{COMMAND}.index_repository_task") as index_repository_task,
            mock.patch(f"{COMMAND}.index_blog_task") as index_blog_task,
        ):
            output = self.run_command("--queue", "--blog")
        index_repository_task.delay.assert_not_called()
        index_blog_task.delay.assert_called_once_with(force=False)
        self.assertIn("Queued the indexing of the blog.", output)
