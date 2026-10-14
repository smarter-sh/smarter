"""
Celery tasks for the mcpserver app.

- :func:`index_repository` brings one repository's index up to date. The MCP server's
  tools queue it for a repository that is not indexed yet.
- :func:`index_repositories` queues :func:`index_repository` for every repository of The
  Smarter Project. Celery Beat runs it hourly, and ``manage.py initialize_platform`` queues
  it. A repository whose branch has not moved costs one request to the GitHub api.

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

from . import indexer
from .repositories import repository_names

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.MCPSERVER_LOGGING]
)

module_prefix = "smarter.apps.mcpserver.tasks."


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
        "%s %s is %s at %s.",
        logging.formatted_text(module_prefix + "index_repository()"),
        name,
        index.status,
        index.commit_sha,
    )
    return str(index.status)


@app.task(queue=smarter_settings.llmclient_tasks_celery_task_queue)
def index_repositories(force: bool = False) -> int:
    """
    Queue :func:`index_repository` for every repository of The Smarter Project.

    :param force: Index each repository even if its latest commit is already indexed.
    :returns: The number of repositories queued.
    :rtype: int
    """
    names = repository_names()
    for name in names:
        index_repository.delay(name, force=force)
    return len(names)


__all__ = ["index_repositories", "index_repository"]
