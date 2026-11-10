"""
The health of the platform's backing services: its health checks, its Celery task queues and its database.

The MCPServer's staff-only ``platform_status`` tool
(:class:`~smarter.apps.mcpserver.protocol.tools.status.PlatformStatusTool`) uses this module to tell whether a
problem that a user reports, e.g. slowness, or a prompt that never finishes, comes from the services
that the platform depends on. It reads:

- **the health checks** of the web console dashboard's Service Health widget: whether the database
  answers a query, the cache keeps a value, the Celery broker accepts a connection, and a Celery worker
  answers a ping. :func:`health_checks` runs the dashboard's own checks,
  :func:`~smarter.apps.dashboard.views.views.api.service_health.run_health_checks`, rather than a copy
  of them, and runs them now, rather than reading the dashboard's one-minute cache.
- **the depth of each Celery task queue**: how many tasks wait for a worker. A queue that grows means
  that the workers are behind, or down, and that background work, e.g. a deploy, is late.
- **the database's load**: its open connections, its running queries, and its slow queries. A database
  that is near its connection limit refuses new requests.

Nothing is cached, and nothing is written. Each function reads the service once when it is called.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from amqp.exceptions import ChannelError
from django.db import connection

from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

if TYPE_CHECKING:
    from kombu.transport.virtual import Channel

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

NOT_FOUND = "404"
"""
The reply code of a passive queue declaration for a queue that the broker does not hold, e.g. an empty one on Redis.

It is text: kombu's Redis transport gives the code as the string ``"404"``, where an AMQP broker gives
the number. :func:`queue_depth` compares both as text.
"""

DATABASE_STATUS = ("Threads_connected", "Threads_running", "Slow_queries", "Aborted_connects", "Uptime")
"""
The MariaDB status counters that :func:`database_load` reads, with ``SHOW GLOBAL STATUS``.

``Threads_connected`` is the open connections, ``Threads_running`` the queries running now,
``Slow_queries`` the queries slower than ``long_query_time`` since the server started,
``Aborted_connects`` the connections that failed, and ``Uptime`` the seconds since the server started.
"""


def task_queues() -> tuple[str, ...]:
    """
    Name the platform's Celery task queues.

    :returns: The default queue, which runs most background work, e.g. prompts' follow-ups, and the
        infrastructure queue, which runs deploys, DNS and certificate work, from
        ``smarter_settings.llmclient_tasks_celery_task_queue`` and
        ``smarter_settings.infrastructure_tasks_celery_task_queue``.
    """
    default_queue = smarter_settings.llmclient_tasks_celery_task_queue
    infrastructure_queue = smarter_settings.infrastructure_tasks_celery_task_queue
    return (default_queue, infrastructure_queue)


def queue_depths() -> dict[str, Optional[int]]:
    """
    Count the tasks that wait in each Celery queue, for a worker to run them.

    Each queue is declared *passively* on the broker: the broker reports how many messages the queue
    holds, and does not create a queue that does not exist. A queue that cannot be read is reported
    as None, rather than as empty, so that "unknown" is never mistaken for "no backlog". It never
    raises: a broker that cannot be reached makes every queue None, and is logged.

    Side effects: one connection to the Celery broker (Redis), which is closed before it returns.
    Nothing is written to a queue.

    :returns: The number of waiting tasks of each queue of :func:`task_queues`, by the queue's name, or
        None for a queue that could not be read.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.lib.celery_conf import APP

    queues = task_queues()
    depths: dict[str, Optional[int]] = {}
    try:
        with APP.connection_for_read() as broker:
            channel = broker.default_channel
            for queue in queues:
                # kombu types default_channel as StdChannel, which doesn't declare the queue_declare()
                # that the broker's channel has.
                depths[queue] = queue_depth(channel, queue)  # type: ignore[arg-type]
    # pylint: disable=broad-except
    except Exception as e:
        logger.warning("%s.queue_depths() could not reach the broker: %s", logger_prefix, e)
        for queue in queues:
            depths[queue] = None
    return depths


def queue_depth(channel: "Channel", queue: str) -> Optional[int]:
    """
    Count the tasks that wait in one Celery queue.

    The queue is declared passively, which asks the broker for the queue's size without creating it.
    On Redis, the platform's broker, a queue is a list, and Redis deletes a list when its last item is
    taken. So kombu answers an empty queue with "404 NOT_FOUND", exactly as for a queue that was never
    used. Both mean that no task waits, so this answer is a depth of zero, not an error.

    :param channel: An open channel of the Celery broker, ``connection.default_channel``.
    :param queue: The queue's name.
    :returns: The number of waiting tasks, or None if the broker failed to answer for another reason,
        which is logged.
    """
    try:
        declared = channel.queue_declare(queue=queue, passive=True)
    except ChannelError as e:
        if str(e.reply_code) == NOT_FOUND:
            return 0
        logger.warning("%s.queue_depth() could not read %s: %s", logger_prefix, queue, e)
        return None
    # pylint: disable=broad-except
    except Exception as e:
        logger.warning("%s.queue_depth() could not read %s: %s", logger_prefix, queue, e)
        return None
    return int(declared.message_count)


@dataclass
class DatabaseLoad:
    """
    The load of the platform's MariaDB database, as ``platform_status`` reports it.

    :func:`database_load` builds it from MariaDB's status counters. Each field is None if MariaDB did
    not report it.
    """

    connections: Optional[int] = None
    """The open connections, from every pod of every component (``Threads_connected``)."""

    max_connections: Optional[int] = None
    """The most connections that MariaDB accepts (``max_connections``).

    Beyond it, new connections are refused.
    """

    running: Optional[int] = None
    """The queries running now (``Threads_running``).

    Many, for long, means that queries wait on each other.
    """

    slow_queries: Optional[int] = None
    """The queries slower than ``long_query_time`` since the server started (``Slow_queries``)."""

    aborted_connects: Optional[int] = None
    """The connections that failed since the server started, e.g. with a bad password (``Aborted_connects``)."""

    uptime_seconds: Optional[int] = None
    """The seconds since the server started (``Uptime``).

    A small number means that it restarted recently.
    """


def as_number(value: Optional[str]) -> Optional[int]:
    """
    Convert a MariaDB status or variable value, which is text, into a number.

    :param value: The value, e.g. ``"42"``, or None if MariaDB did not report it.
    :returns: The number, or None if the value is missing or is not a whole number.
    """
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def database_load() -> DatabaseLoad:
    """
    Read the database's connections, running queries and slow queries.

    Side effects: two read-only queries on the platform's database connection,
    ``SHOW GLOBAL STATUS`` for the counters of :data:`DATABASE_STATUS`, and
    ``SHOW VARIABLES LIKE 'max_connections'``. Nothing is written.

    :returns: The database's load.
    :raises django.db.Error: If the database cannot be queried, e.g. because it is down. The caller
        reports that, rather than a load of zero.
    """
    placeholders = ", ".join(["%s"] * len(DATABASE_STATUS))
    status_query = f"SHOW GLOBAL STATUS WHERE Variable_name IN ({placeholders})"  # nosec B608: placeholders only
    with connection.cursor() as cursor:
        cursor.execute(status_query, DATABASE_STATUS)
        status_rows = cursor.fetchall()
        cursor.execute("SHOW VARIABLES LIKE 'max_connections'")
        variable_rows = cursor.fetchall()

    status = {}
    for name, value in status_rows:
        status[str(name)] = value
    variables = {}
    for name, value in variable_rows:
        variables[str(name)] = value

    return DatabaseLoad(
        connections=as_number(status.get("Threads_connected")),
        max_connections=as_number(variables.get("max_connections")),
        running=as_number(status.get("Threads_running")),
        slow_queries=as_number(status.get("Slow_queries")),
        aborted_connects=as_number(status.get("Aborted_connects")),
        uptime_seconds=as_number(status.get("Uptime")),
    )


@dataclass(frozen=True)
class HealthCheckResult:
    """One of the dashboard's health checks, as ``platform_status`` reports it."""

    name: str
    """The check's name, e.g. ``Workers``."""

    healthy: bool
    """Whether it passed."""

    error: str = ""
    """Why it failed, e.g. ``TimeoutError: Timeout connecting to server``, or an empty string if it passed."""


def health_checks() -> list[HealthCheckResult]:
    """
    Run the web console dashboard's health checks, now.

    These are the checks of the dashboard's Service Health widget,
    :data:`~smarter.apps.dashboard.views.views.api.service_health.HEALTH_CHECKS`: ``Database``,
    ``Cache``, ``Task Broker`` and ``Workers``. They run now, uncached, because a help desk question is
    about this moment. A check that raises counts as failed: it never raises.

    Side effects: a ``SELECT 1`` on the database, a value written to the cache and deleted, a
    connection to the Celery broker, and a ping of the Celery workers, which waits up to half a second
    for their answers.

    :returns: Each check's name, whether it passed, and why not, so that a failure can be diagnosed.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.dashboard.views.views.api.service_health import (
        run_health_checks,
    )

    results = []
    for check in run_health_checks():
        name = str(check["name"])
        healthy = bool(check["healthy"])
        error = str(check.get("error") or "")
        result = HealthCheckResult(name=name, healthy=healthy, error=error)
        results.append(result)
    return results


__all__ = ["DatabaseLoad", "HealthCheckResult", "database_load", "health_checks", "queue_depths", "task_queues"]
