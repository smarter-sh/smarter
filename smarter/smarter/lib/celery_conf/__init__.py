"""
The Smarter platform's Celery app.

It is configured from the Django settings whose names start with ``CELERY_``, and finds the
``tasks`` modules of every installed Django app.
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

# Load task modules from all registered Django APP configs.
APP.autodiscover_tasks()

APP.conf.broker_connection_retry_on_startup = True
