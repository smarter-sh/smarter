"""
Models of the MCPServer app: the search index of The Smarter Project's repositories, and the audit trail of the operations tools.

:class:`RepositoryIndex` records, for each repository of
:data:`~smarter.apps.mcpserver.services.repositories.SMARTER_PROJECT_REPOSITORIES`, the commit that
is indexed, and :class:`RepositoryFile` holds the text of each of its files. The index is
built by :func:`smarter.apps.mcpserver.services.indexing.github.index_repository`, and replaced whenever the
repository's branch moves to a new commit.

:class:`OperationsToolCall` records every call to a staff-only tool of the MCPServer
(:mod:`smarter.apps.mcpserver.protocol.operations`): who called it, for which help desk ticket,
with which arguments, and whether it failed. The tools read logs and users' data, so each call
is kept until a superuser deletes it.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.conf import settings
from django.db import models

from smarter.lib.django.models import TimestampedModel


class RepositoryIndexStatus(models.TextChoices):
    """
    The status of a repository's index, in :attr:`RepositoryIndex.status`.

    A repository starts ``pending``. It becomes ``ready`` once it is indexed, and stays
    ``ready`` when a later refresh fails, so that its last good index is still searched. It is
    ``failed`` only when it has never been indexed.
    """

    PENDING = "pending", "Pending"
    """The repository has not been indexed yet."""
    READY = "ready", "Ready"
    """The repository is indexed.

    The last attempt to refresh it may have failed: see ``error``.
    """
    FAILED = "failed", "Failed"
    """The repository could not be indexed, and has no index."""


class RepositoryFileKind(models.TextChoices):
    """
    What a file of a repository is, in :attr:`RepositoryFile.kind`.

    The search tools use it to search only the documentation, or only the code.
    """

    DOCUMENTATION = "documentation", "Documentation"
    """Prose, e.g. reStructuredText and Markdown."""
    CODE = "code", "Code"
    """Source code and configuration."""


class RepositoryIndex(TimestampedModel):
    """
    The index of one of The Smarter Project's repositories, or of its blog.

    There is one row per repository of
    :data:`~smarter.apps.mcpserver.services.repositories.SMARTER_PROJECT_REPOSITORIES`, plus one for the
    blog, whose ``repository`` is the blog's name, e.g. ``blog.smarter.sh``. The row records
    which commit is indexed, and whether the last attempt to index it failed. The text of the
    indexed files is in its :class:`RepositoryFile` rows, ``index.files``.

    It is written only by the indexers,
    :func:`smarter.apps.mcpserver.services.indexing.github.index_repository` and
    :func:`smarter.apps.mcpserver.services.indexing.blog.index_blog`.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "Repository Indexes"
        ordering = ["repository"]

    #: The repository's name, e.g. ``smarter-cli``, or the blog's, e.g. ``blog.smarter.sh``. Unique.
    repository = models.CharField(max_length=100, unique=True, help_text="The repository's name, e.g. smarter-cli.")
    #: The SHA of the commit whose files are indexed, or None if nothing is indexed yet. The blog,
    #: which has no commits, stores a fingerprint of its posts here.
    commit_sha = models.CharField(max_length=40, blank=True, null=True, help_text="The indexed commit.")
    #: Whether the repository has an index to search: see :class:`RepositoryIndexStatus`.
    status = models.CharField(
        max_length=16, choices=RepositoryIndexStatus.choices, default=RepositoryIndexStatus.PENDING
    )
    #: When the indexed commit was indexed, or None if nothing is indexed yet.
    indexed_at = models.DateTimeField(blank=True, null=True, help_text="When the indexed commit was indexed.")
    #: How many files of the indexed commit are stored, as :class:`RepositoryFile` rows.
    file_count = models.PositiveIntegerField(default=0)
    #: The total size, in bytes, of the stored files.
    total_bytes = models.PositiveBigIntegerField(default=0)
    #: Why the last attempt to index the repository failed, or None if it succeeded. A ``ready``
    #: index with an error is still searched, at its previous commit.
    error = models.TextField(blank=True, null=True, help_text="Why the last attempt to index the repository failed.")

    def __str__(self) -> str:
        """
        Return the index as people read it, e.g. ``smarter-cli@0123abc ready``.

        :returns: The repository, the first seven characters of the indexed commit, and the status.
        """
        return f"{self.repository}@{str(self.commit_sha or '')[:7]} {self.status}"

    @property
    def is_ready(self) -> bool:
        """
        Whether the repository has an index to search.

        :returns: True if :attr:`status` is ``ready``, even if the last refresh failed.
        """
        return self.status == RepositoryIndexStatus.READY


class RepositoryFile(TimestampedModel):
    """
    One text file of an indexed repository, or one post of the blog.

    The indexers replace every file of an index when its repository moves to a new commit.
    The MCP server's tools search their ``content``, and read it back by ``path``. A file is
    unique in its index by its path.
    """

    # pylint: disable=C0115
    class Meta:
        ordering = ["index", "path"]
        constraints = [models.UniqueConstraint(fields=["index", "path"], name="mcpserver_unique_repository_file")]
        indexes = [models.Index(fields=["index", "kind"])]

    #: The index that the file belongs to. Its files are deleted with it.
    index = models.ForeignKey(RepositoryIndex, on_delete=models.CASCADE, related_name="files")
    #: The file's path in the repository, e.g. ``docs/source/index.rst``, or a post's permalink path.
    path = models.CharField(max_length=512, help_text="The file's path in the repository.")
    #: Whether the file is documentation or code: see :class:`RepositoryFileKind`.
    kind = models.CharField(max_length=16, choices=RepositoryFileKind.choices)
    #: A document's first heading, or a post's title. Empty for code.
    title = models.CharField(max_length=255, blank=True, default="", help_text="A document's first heading.")
    #: The file's text, which the tools search and read.
    content = models.TextField()
    #: The file's size, in bytes.
    size = models.PositiveIntegerField(help_text="Bytes.")
    #: How many lines the file has, counted when it was indexed.
    line_count = models.PositiveIntegerField()

    def __str__(self) -> str:
        """
        Return the file as people read it, e.g. ``smarter-cli:README.md``.

        Side effect: a query of its index, unless the index is already loaded.

        :returns: The repository's name and the file's path.
        """
        return f"{self.index.repository}:{self.path}"


class OperationsToolCall(TimestampedModel):
    """
    One call to a staff-only tool of the MCPServer, for the audit trail.

    The operations tools read logs and users' data, so the server writes a row for every
    call, whether it succeeded or not: who called it, for which help desk ticket, with which
    arguments, and how long its result was. The rows are read-only in the Django admin
    (:class:`~smarter.apps.mcpserver.admin.OperationsToolCallAdmin`), and are kept until a
    superuser deletes them.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name = "Operations Tool Call"
        indexes = [models.Index(fields=["ticket"])]

    #: The staff user whose api key called the tool. Set to None when the user is deleted, so
    #: that the row outlives them: see :attr:`username`.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="The staff user whose api key called the tool. Empty once the user is deleted: see username.",
    )
    #: The user's username at the time of the call, which outlives the user.
    username = models.CharField(
        max_length=150, help_text="The user's username at the time of the call, which outlives the user."
    )
    #: The tool's name, e.g. ``search_logs``.
    tool = models.CharField(max_length=100, help_text="The tool, e.g. search_logs.")
    #: The help desk ticket, or reason, that the caller gave for the call. Every operations
    #: tool requires one. Indexed, to find every call made for a ticket.
    ticket = models.CharField(max_length=200, help_text="The help desk ticket, or reason, that the caller gave.")
    #: The tool call's other arguments, without the ticket.
    arguments = models.JSONField(default=dict, help_text="The tool call's other arguments.")
    #: Whether the tool returned an error instead of a result.
    is_error = models.BooleanField(default=False, help_text="Whether the tool returned an error.")
    #: The length of the tool's result, in characters.
    characters = models.PositiveIntegerField(default=0, help_text="The length of the result.")

    def __str__(self) -> str:
        """
        Return the call as people read it, e.g. ``2026-11-02 14:05 jane search_logs [HD-1234]``.

        :returns: When it was made, by whom, the tool, and the ticket.
        """
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.username} {self.tool} [{self.ticket}]"


__all__ = [
    "OperationsToolCall",
    "RepositoryFile",
    "RepositoryFileKind",
    "RepositoryIndex",
    "RepositoryIndexStatus",
]
