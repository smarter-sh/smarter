"""
Celery tasks for the mcpclient app.

- :func:`refresh_mcpclient` connects to one MCPClient's MCP server, refreshes its cached
  catalog, and records the result in the MCPClient's status. It is queued whenever an
  MCPClient is saved.
- :func:`refresh_mcpclients` refreshes every active MCPClient. Celery Beat runs it hourly.

A server that cannot be reached is recorded in the MCPClient's status. It is not an error
of the task, so the tasks do not retry.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from typing import Optional

from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from ..caching import get_cached_catalog
from ..exceptions import SmarterMCPClientException
from ..models import MCPClient

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.MCPCLIENT_LOGGING]
)

module_prefix = "smarter.apps.mcpclient.tasks."


@app.task(queue=smarter_settings.llmclient_tasks_celery_task_queue)
def refresh_mcpclient(mcpclient_id: int) -> Optional[str]:
    """
    Connect to an MCPClient's MCP server, refresh its catalog, and record the result.

    :param mcpclient_id: The id of the MCPClient.
    :returns: The MCPClient's connection status, or ``None`` if it does not exist.
    :rtype: Optional[str]
    """
    mcpclient = MCPClient.objects.select_related("credentials").filter(pk=mcpclient_id).first()
    if mcpclient is None:
        logger.warning(
            "%s MCPClient %s does not exist.", formatted_text(module_prefix + "refresh_mcpclient()"), mcpclient_id
        )
        return None
    try:
        catalog = get_cached_catalog(mcpclient, refresh=True)
        logger.info(
            "%s %s is connected to %s, with %s tools.",
            formatted_text(module_prefix + "refresh_mcpclient()"),
            mcpclient.name,
            catalog.server_name,
            len(mcpclient.tools or []),
        )
    except SmarterMCPClientException as e:
        logger.warning(
            "%s %s could not connect: %s", formatted_text(module_prefix + "refresh_mcpclient()"), mcpclient.name, e
        )
    return mcpclient.status


@app.task(queue=smarter_settings.llmclient_tasks_celery_task_queue)
def refresh_mcpclients() -> int:
    """
    Queue :func:`refresh_mcpclient` for every active MCPClient.

    :returns: The number of MCPClients queued.
    :rtype: int
    """
    mcpclient_ids = list(MCPClient.objects.filter(is_active=True).values_list("id", flat=True))
    for mcpclient_id in mcpclient_ids:
        refresh_mcpclient.delay(mcpclient_id)
    return len(mcpclient_ids)


__all__ = ["refresh_mcpclient", "refresh_mcpclients"]
