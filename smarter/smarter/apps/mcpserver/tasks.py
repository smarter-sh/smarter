"""
Celery tasks of the MCPServer app, which keep the MCPServer's index of the repositories and the blog up to date.

- :func:`index_repository` brings one repository's index up to date. The MCP server's
  tools queue it for a repository that is not indexed yet.
- :func:`index_blog` brings the blog's index up to date with its published posts.
- :func:`index_repositories` queues :func:`index_repository` for every repository of The
  Smarter Project, and :func:`index_blog`. Celery Beat runs it hourly, and ``manage.py
  initialize_platform`` queues it. A repository whose branch has not moved costs one
  request to the GitHub api, and the blog one request per 100 posts.

A repository that cannot be indexed is recorded in its index's ``error``. It is not an error
of the task, so the tasks do not retry.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from smarter.apps.mcpserver.services.indexing import blog, github
from smarter.apps.mcpserver.services.repositories import repository_names
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.MCPSERVER_LOGGING]
)
logger_prefix = logging.SmarterFormattedText.text(__name__)


@app.task(queue=smarter_settings.llmclient_tasks_celery_task_queue)
def index_repository(name: str, force: bool = False) -> str:
    """
    Bring a repository's index up to date with the latest commit of its branch.

    Runs :func:`smarter.apps.mcpserver.services.indexing.github.index_repository` in the Celery worker.
    Side effects: a request to the GitHub api for the branch's latest commit and, when it has
    moved, a download of the repository's archive, and the replacement of its
    :class:`~smarter.apps.mcpserver.models.RepositoryFile` rows. The indexer then sends
    ``mcpserver_repository_indexed``, which makes the cached tool results stale, or
    ``mcpserver_repository_index_failed``.

    :param name: The repository's name, e.g. ``smarter-cli``.
    :param force: Index the repository even if its latest commit is already indexed.
    :returns: The index's status, e.g. ``ready``.
    :rtype: str
    :raises SmarterMCPServerIndexError: If ``name`` is not a repository of The Smarter Project.
    """
    index = github.index_repository(name, force=force)
    logger.info(
        "%s.index_repository() %s is %s at %s.",
        logger_prefix,
        name,
        index.status,
        index.commit_sha,
    )
    status = str(index.status)
    return status


@app.task(queue=smarter_settings.llmclient_tasks_celery_task_queue)
def index_blog(force: bool = False) -> str:
    """
    Bring the blog's index up to date with its published posts.

    Runs :func:`smarter.apps.mcpserver.services.indexing.blog.index_blog` in the Celery worker. Side
    effects: requests to the blog's WordPress REST api, one per 100 posts, and, when the posts
    changed, the replacement of the blog's
    :class:`~smarter.apps.mcpserver.models.RepositoryFile` rows and a signal that makes the
    cached tool results stale.

    :param force: Index the posts even if they are already indexed.
    :returns: The index's status, e.g. ``ready``.
    :rtype: str
    """
    index = blog.index_blog(force=force)
    logger.info(
        "%s.index_blog() %s is %s: %s posts.",
        logger_prefix,
        index.repository,
        index.status,
        index.file_count,
    )
    status = str(index.status)
    return status


@app.task(queue=smarter_settings.llmclient_tasks_celery_task_queue)
def index_repositories(force: bool = False) -> int:
    """
    Queue :func:`index_repository` for every repository of The Smarter Project, and :func:`index_blog`.

    Each repository is indexed by its own task, so that one slow or failing repository does
    not hold up the others. Side effects: one Celery task queued per repository, and one for
    the blog.

    :param force: Index each repository, and the blog, even if they are already indexed.
    :returns: The number of repositories queued, not counting the blog.
    :rtype: int
    """
    names = repository_names()
    for name in names:
        index_repository.delay(name, force=force)
    index_blog.delay(force=force)
    return len(names)


__all__ = ["index_blog", "index_repositories", "index_repository"]
