"""
The Smarter platform's Celery app.

It is configured from the Django settings whose names start with ``CELERY_``, and finds the
``tasks`` modules of every installed Django app. In the tool worker, ``smarter-worker-tools``, it
registers only the tool worker's own task (:data:`TOOL_WORKER_TASKS`).
"""

import logging

from celery import Celery
from celery.signals import worker_init, worker_process_init

APP = Celery("smarter")
"""The Celery app that the Smarter workers and Celery Beat run."""
APP.conf.task_protocol = 1
# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
APP.config_from_object("django.conf:settings", namespace="CELERY")


def set_redbeat_conf(app: Celery) -> None:
    """
    Set RedBeat's settings on the app under their own, unprefixed names.

    RedBeat decides whether ``redbeat_redis_url`` and ``redbeat_redis_options`` are set by looking for
    those exact keys in ``app.conf.keys()``. Under the ``CELERY`` namespace the keys are still
    ``CELERY_REDBEAT_REDIS_URL`` and ``CELERY_REDBEAT_REDIS_OPTIONS``, so it found neither, warned that
    it falls back to the broker's url and transport options, and RedBeat 2.5.0 removes that fallback
    (issue #945). Setting them unprefixed is what RedBeat finds. ``redbeat_lock_timeout`` is set the
    same way (issue #964).

    :param app: The Celery app that Celery Beat runs.
    :returns: None
    """
    # pylint: disable=import-outside-toplevel
    from django.conf import settings

    app.conf.redbeat_redis_url = settings.CELERY_REDBEAT_REDIS_URL
    app.conf.redbeat_redis_options = settings.CELERY_REDBEAT_REDIS_OPTIONS
    app.conf.redbeat_lock_timeout = settings.CELERY_REDBEAT_LOCK_TIMEOUT


set_redbeat_conf(APP)


def set_result_backend(app: Celery) -> None:
    """
    Store task results in the broker's Redis, unless a result backend is configured.

    The tool runner (``smarter.apps.llmtool.runner``) waits for the result of ``run_tool_call``, which the
    tool worker returns. The broker's url, as the deployment sets it, e.g. with
    ``DJANGO_CELERY_BROKER_URL``, is read here, after the settings' overrides, so that the results go to
    the same Redis. ``CELERY_TASK_IGNORE_RESULT`` keeps every other task's result out of it.

    :param app: The Celery app.
    :returns: None
    """
    if not app.conf.result_backend:
        app.conf.update(result_backend=app.conf.broker_url)


set_result_backend(APP)


def configure_tool_worker(app: Celery) -> None:
    """
    In the tool worker, consume its queue without declaring it, and take no remote control.

    The tool worker authenticates to Redis as its own ACL user, which may touch only its queue's keys, its
    results and a few cache keys (ADR-030, rule 8). Declaring a queue adds it to kombu's routing set,
    ``_kombu.binding.<queue>``, which the app reads to route each task. A tool worker that could write that
    set could bind its queue's exchange to another queue, such as the infrastructure queue, whose worker
    holds the platform's credentials, and the app would deliver tool calls, with their credentials, there.
    So the queue is ``no_declare``: the app declares it, when it sends the first tool call. The same goes
    for the Extension worker (issue #1077), which runs the same code on the Extensions queue: both queues
    are defined, ``no_declare``, and each worker's ``-Q`` picks its own.

    Remote control (``celery inspect``, ``celery control``), mingle, gossip and heartbeats all go through
    fanout exchanges and pidbox queues, which the ACL user can't reach. The worker turns off remote control
    here, and the others with ``--without-mingle --without-gossip --without-heartbeat`` on its command line.
    Its liveness probe looks for its process instead of pinging it.

    Only the tool worker (``smarter_settings.database_unavailable``): the other workers are unchanged.

    :param app: The Celery app.
    :returns: None
    """
    # pylint: disable=import-outside-toplevel
    from kombu import Exchange, Queue

    from smarter.common.conf import smarter_settings

    if not smarter_settings.database_unavailable:
        return
    queue_names = (
        smarter_settings.app_tools_tasks_celery_task_queue,
        smarter_settings.app_extensions_tasks_celery_task_queue,
    )
    queues = []
    for queue_name in queue_names:
        # the exchange and routing key that Celery gives a queue it creates, as the app does when it sends.
        queue = Queue(queue_name, Exchange(queue_name), routing_key=queue_name, no_declare=True)
        queues.append(queue)
    app.conf.task_queues = queues
    app.conf.worker_enable_remote_control = False


configure_tool_worker(APP)


class HideTaskDataFilter(logging.Filter):
    """
    Keep a task's arguments and result out of Celery's log records.

    Celery logs each task's success with its return value, and passes its arguments, and those of a
    failed task, in the record's ``data``. In the tool worker, the arguments are a tool call, with its
    credentials, and the result is what the tool answered. Its pool also logs, at DEBUG, each task's
    message, which holds the arguments: that record is dropped.
    """

    HIDDEN = "(hidden)"
    """What replaces a hidden value."""

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Hide the task data in a record of Celery's, or drop the record.

        :param record: The record.
        :returns: False for the pool's record of a task's message; otherwise True.
        """
        if record.name == "celery.pool":
            return not str(record.msg).startswith("TaskPool: Apply")
        context = record.args if isinstance(record.args, dict) else None
        for values in (context, getattr(record, "data", None)):
            if isinstance(values, dict):
                for key in ("return_value", "args", "kwargs"):
                    if key in values:
                        values[key] = self.HIDDEN
        return True


TASK_DATA_LOGGERS = ("celery.app.trace", "celery.pool")
"""The loggers whose records can hold a task's arguments or result."""


def hide_tool_calls_from_logs(**kwargs) -> None:
    """
    In the tool worker, keep every task's arguments and result out of Celery's log.

    Connected to ``worker_init`` and ``worker_process_init``, so that the pool's processes have the
    filter too. Only the tool worker (``smarter_settings.database_unavailable``), whose tasks are tool
    calls: the other workers' logs are unchanged.

    :param kwargs: The signal's arguments, unused.
    :returns: None
    """
    # pylint: disable=import-outside-toplevel
    from smarter.common.conf import smarter_settings

    if not smarter_settings.database_unavailable:
        return
    for name in TASK_DATA_LOGGERS:
        task_logger = logging.getLogger(name)
        if not any(isinstance(f, HideTaskDataFilter) for f in task_logger.filters):
            task_logger.addFilter(HideTaskDataFilter())


worker_init.connect(hide_tool_calls_from_logs, weak=False)
worker_process_init.connect(hide_tool_calls_from_logs, weak=False)


TOOL_WORKER_TASKS = ("smarter.apps.llmtool.tasks.run_tool_call",)
"""The names of the only tasks that the tool worker, ``smarter-worker-tools``, runs (ADR-038)."""

TOOL_WORKER_TASK_PACKAGES = ("smarter.apps.llmtool",)
"""The packages whose ``tasks`` modules the tool worker imports: those of :data:`TOOL_WORKER_TASKS`."""

CELERY_BUILTIN_TASK_PREFIX = "celery."
"""The prefix of Celery's own tasks, e.g. ``celery.chord_unlock``, which every worker keeps."""


def task_packages() -> list[str]:
    """
    Name the packages whose ``tasks`` modules the Celery app imports.

    Every installed Django app's, except in the tool worker (``smarter_settings.database_unavailable``),
    which imports only :data:`TOOL_WORKER_TASK_PACKAGES`. The tool worker runs third parties' code,
    so it imports no more of the platform than it needs. It is called lazily, when the app is
    finalized, after Django is set up.

    :returns: The packages' dotted names.
    """
    # pylint: disable=import-outside-toplevel
    from django.apps import apps

    from smarter.common.conf import smarter_settings

    if smarter_settings.database_unavailable:
        return list(TOOL_WORKER_TASK_PACKAGES)
    packages = [config.name for config in apps.get_app_configs()]
    return packages


def keep_only_tool_worker_tasks(app: Celery) -> list[str]:
    """
    Remove every task from the app's registry except :data:`TOOL_WORKER_TASKS` and Celery's own.

    Django's app loading imports many apps' ``tasks`` modules, through their receivers, whatever
    :func:`task_packages` says, and so registers tasks that deploy LLMClients, write DNS records or
    charge accounts. The tool worker must never run them. A worker rejects a message for a task that
    isn't in its registry ("Received unregistered task"), so after this it runs nothing but tool calls,
    whatever lands on its queue.

    :param app: The Celery app.
    :returns: The names of the tasks removed, sorted.
    :raises SmarterConfigurationError: If a task of :data:`TOOL_WORKER_TASKS` isn't registered: the
        worker would run nothing.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.common.exceptions import SmarterConfigurationError

    registry = app.tasks
    for name in TOOL_WORKER_TASKS:
        if name not in registry:
            raise SmarterConfigurationError(f"The tool worker's task {name} is not registered.")
    removed = []
    for name in sorted(registry.keys()):
        if name in TOOL_WORKER_TASKS:
            continue
        if name.startswith(CELERY_BUILTIN_TASK_PREFIX):
            continue
        registry.unregister(name)
        removed.append(name)
    return removed


def restrict_tool_worker_tasks(**kwargs) -> None:
    """
    In the tool worker, keep only its own tasks in the registry (:func:`keep_only_tool_worker_tasks`).

    Connected to ``worker_init``, which the worker sends before it prints its banner and before its
    pool's processes fork, so that they inherit the restricted registry. Only the tool worker
    (``smarter_settings.database_unavailable``): the other workers keep every task.

    :param kwargs: The signal's arguments, unused.
    :returns: None
    """
    # pylint: disable=import-outside-toplevel
    from smarter.common.conf import smarter_settings

    if not smarter_settings.database_unavailable:
        return
    keep_only_tool_worker_tasks(APP)


worker_init.connect(restrict_tool_worker_tasks, weak=False)


def run_worker_startup_checks(**kwargs) -> None:
    """
    Check, when a worker starts, what it depends on, the way the settings check AWS.

    Connected to ``worker_init``, so that the checks run once, in the worker's main process, before its
    pool's processes fork. The tool worker (``smarter_settings.database_unavailable``) checks its isolation
    (ADR-038) and its Redis user (ADR-030), then logs one line that sums them up, with the tasks it runs:
    :func:`restrict_tool_worker_tasks`, connected before this, has already left only its own in the
    registry. Every other worker checks its database, cache and Kubernetes cluster. See
    :mod:`smarter.apps.infrastructure.startup`.

    :param kwargs: The signal's arguments, unused.
    :returns: None
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.infrastructure.startup import (
        TOOL_WORKER_CHECKS,
        WORKER_CHECKS,
        log_tool_worker_readiness,
        run_startup_checks,
    )
    from smarter.common.conf import smarter_settings

    if not smarter_settings.database_unavailable:
        run_startup_checks(WORKER_CHECKS)
        return
    results = run_startup_checks(TOOL_WORKER_CHECKS)
    tasks = []
    for name in sorted(APP.tasks.keys()):
        if not name.startswith(CELERY_BUILTIN_TASK_PREFIX):
            tasks.append(name)
    log_tool_worker_readiness(results, tasks, smarter_settings.tool_worker_queue)


worker_init.connect(run_worker_startup_checks, weak=False)

# Load the task modules of the packages that task_packages() names, when the app is finalized.
APP.autodiscover_tasks(task_packages)

APP.conf.broker_connection_retry_on_startup = True
