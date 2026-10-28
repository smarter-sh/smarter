"""
Celery tasks for the mcpserver app.

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

from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from . import blog, indexer
from .repositories import repository_names

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.MCPSERVER_LOGGING]
)
logger_prefix = logging.SmarterFormattedText.text(__name__)


@app.task(queue=smarter_settings.llmclient_tasks_celery_task_queue)
def index_repository(name: str, force: bool = False) -> str:
    """
    Bring a repository's index up to date with the latest commit of its branch.

    :param name: The repository's name, e.g. ``smarter-cli``.
    :param force: Index the repository even if its latest commit is already indexed.
    :returns: The index's status.
    :rtype: str
    """
    index = indexer.index_repository(name, force=force)
    logger.info(
        "%s.index_repository() %s is %s at %s.",
        logger_prefix,
        name,
        index.status,
        index.commit_sha,
    )
    return str(index.status)


@app.task(queue=smarter_settings.llmclient_tasks_celery_task_queue)
def index_blog(force: bool = False) -> str:
    """
    Bring the blog's index up to date with its published posts.

    :param force: Index the posts even if they are already indexed.
    :returns: The index's status.
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
    return str(index.status)


@app.task(queue=smarter_settings.llmclient_tasks_celery_task_queue)
def index_repositories(force: bool = False) -> int:
    """
    Queue :func:`index_repository` for every repository of The Smarter Project, and :func:`index_blog`.

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
