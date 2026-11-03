"""
The indexes that are ready to read, and the indexing of those that are not.

Every service that reads the index (:mod:`~smarter.apps.mcpserver.services.search` and
:mod:`~smarter.apps.mcpserver.services.reading`) asks here first. A repository, or the blog, that
is not indexed yet is queued for indexing, with a Celery task, at most once every
:data:`INDEX_QUEUE_TIMEOUT` seconds, and the caller is told to try again in a few minutes.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from typing import Sequence

from cache_results import lazy_cache

from smarter.apps.mcpserver.exceptions import SmarterMCPServerServiceError
from smarter.apps.mcpserver.models import RepositoryIndex
from smarter.apps.mcpserver.services.repositories import (
    ProjectBlog,
    ProjectRepository,
    ProjectSource,
)

INDEX_QUEUE_TIMEOUT = 600
"""Seconds during which a repository that is not indexed is queued for indexing only once."""


def queue_indexing_key(name: str) -> str:
    """
    Return the cache key that remembers that a repository was queued for indexing.

    :param name: The repository's name, or the blog's.
    :returns: The key.
    """
    key = f"smarter.apps.mcpserver.services.indexing.indexes.queue_indexing.{name}"
    return key


def queue_indexing(repository: ProjectSource) -> None:
    """
    Queue a repository, or the blog, that is not indexed for indexing, at most once every :data:`INDEX_QUEUE_TIMEOUT` seconds.

    Many requests may find the same repository not indexed while it is being indexed, so a cache
    key, added only if it is missing, makes sure that only the first of them queues a task.

    **Side effects:** a cache write, and, if the key was not there, a Celery task queued:
    :func:`smarter.apps.mcpserver.tasks.index_blog` or :func:`smarter.apps.mcpserver.tasks.index_repository`.

    :param repository: The repository, or the blog.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.mcpserver.tasks import index_blog, index_repository

    key = queue_indexing_key(repository.name)
    is_first = lazy_cache.add(key, True, timeout=INDEX_QUEUE_TIMEOUT)
    if not is_first:
        return
    if isinstance(repository, ProjectBlog):
        index_blog.delay()
    else:
        index_repository.delay(repository.name)


def ready_indexes(repositories: Sequence[ProjectSource]) -> dict[str, RepositoryIndex]:
    """
    Return the indexes of the repositories that are ready to read, and queue the others for indexing.

    **Side effects:** one database query, and :func:`queue_indexing` for each repository that is not ready.

    :param repositories: The repositories, or the blog.
    :returns: The ready indexes, by repository name.
    """
    names = [repository.name for repository in repositories]
    indexes = {}
    for index in RepositoryIndex.objects.filter(repository__in=names):
        indexes[index.repository] = index

    ready = {}
    for repository in repositories:
        index = indexes.get(repository.name)
        if index is not None and index.is_ready:
            ready[repository.name] = index
        else:
            queue_indexing(repository)
    return ready


def not_indexed_error(names: str) -> SmarterMCPServerServiceError:
    """
    Return the error for repositories that are not indexed yet, and have been queued.

    :param names: The repositories' names, e.g. ``smarter-cli``, or ``The blog, <url>,``.
    :returns: The error, for the caller to raise.
    """
    message = f"{names} has not been indexed yet. Indexing has started: try again in a few minutes."
    error = SmarterMCPServerServiceError(message)
    return error


def require_index(repository: ProjectRepository) -> RepositoryIndex:
    """
    Return a repository's index.

    **Side effects:** see :func:`ready_indexes`.

    :param repository: The repository.
    :returns: Its index.
    :raises SmarterMCPServerServiceError: If the repository is not indexed yet. It is then queued for indexing.
    """
    ready = ready_indexes([repository])
    index = ready.get(repository.name)
    if index is None:
        raise not_indexed_error(repository.name)
    return index


def require_blog_index(blog: ProjectBlog) -> RepositoryIndex:
    """
    Return the blog's index.

    **Side effects:** see :func:`ready_indexes`.

    :param blog: The blog.
    :returns: Its index.
    :raises SmarterMCPServerServiceError: If the blog is not indexed yet. It is then queued for indexing.
    """
    ready = ready_indexes([blog])
    index = ready.get(blog.name)
    if index is None:
        raise not_indexed_error(f"The blog, {blog.url},")
    return index


__all__ = [
    "INDEX_QUEUE_TIMEOUT",
    "not_indexed_error",
    "queue_indexing",
    "queue_indexing_key",
    "ready_indexes",
    "require_blog_index",
    "require_index",
]
