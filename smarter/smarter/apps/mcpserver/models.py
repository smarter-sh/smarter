"""
Models of the MCPServer app: the search index of The Smarter Project's repositories.

:class:`RepositoryIndex` records, for each repository of
:data:`~smarter.apps.mcpserver.repositories.SMARTER_PROJECT_REPOSITORIES`, the commit that
is indexed, and :class:`RepositoryFile` holds the text of each of its files. The index is
built by :func:`smarter.apps.mcpserver.indexer.index_repository`, and replaced whenever the
repository's branch moves to a new commit.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.db import models

from smarter.lib.django.models import TimestampedModel


class RepositoryIndexStatus(models.TextChoices):
    """The status of a repository's index."""

    PENDING = "pending", "Pending"
    """The repository has not been indexed yet."""
    READY = "ready", "Ready"
    """The repository is indexed.

    The last attempt to refresh it may have failed: see ``error``.
    """
    FAILED = "failed", "Failed"
    """The repository could not be indexed, and has no index."""


class RepositoryFileKind(models.TextChoices):
    """What a file of a repository is."""

    DOCUMENTATION = "documentation", "Documentation"
    """Prose, e.g. reStructuredText and Markdown."""
    CODE = "code", "Code"
    """Source code and configuration."""


class RepositoryIndex(TimestampedModel):
    """The index of one of The Smarter Project's repositories."""

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "Repository Indexes"
        ordering = ["repository"]

    repository = models.CharField(max_length=100, unique=True, help_text="The repository's name, e.g. smarter-cli.")
    commit_sha = models.CharField(max_length=40, blank=True, null=True, help_text="The indexed commit.")
    status = models.CharField(
        max_length=16, choices=RepositoryIndexStatus.choices, default=RepositoryIndexStatus.PENDING
    )
    indexed_at = models.DateTimeField(blank=True, null=True, help_text="When the indexed commit was indexed.")
    file_count = models.PositiveIntegerField(default=0)
    total_bytes = models.PositiveBigIntegerField(default=0)
    error = models.TextField(blank=True, null=True, help_text="Why the last attempt to index the repository failed.")

    def __str__(self) -> str:
        return f"{self.repository}@{(self.commit_sha or '')[:7]} {self.status}"

    @property
    def is_ready(self) -> bool:
        """Whether the repository has an index to search."""
        return self.status == RepositoryIndexStatus.READY


class RepositoryFile(TimestampedModel):
    """One text file of an indexed repository."""

    # pylint: disable=C0115
    class Meta:
        ordering = ["index", "path"]
        constraints = [models.UniqueConstraint(fields=["index", "path"], name="mcpserver_unique_repository_file")]
        indexes = [models.Index(fields=["index", "kind"])]

    index = models.ForeignKey(RepositoryIndex, on_delete=models.CASCADE, related_name="files")
    path = models.CharField(max_length=512, help_text="The file's path in the repository.")
    kind = models.CharField(max_length=16, choices=RepositoryFileKind.choices)
    title = models.CharField(max_length=255, blank=True, default="", help_text="A document's first heading.")
    content = models.TextField()
    size = models.PositiveIntegerField(help_text="Bytes.")
    line_count = models.PositiveIntegerField()

    def __str__(self) -> str:
        return f"{self.index.repository}:{self.path}"


__all__ = [
    "RepositoryFile",
    "RepositoryFileKind",
    "RepositoryIndex",
    "RepositoryIndexStatus",
]
