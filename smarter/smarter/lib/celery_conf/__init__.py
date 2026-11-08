"""
The Smarter platform's Celery app.

It is configured from the Django settings whose names start with ``CELERY_``, and finds the
``tasks`` modules of every installed Django app.
"""

from celery import Celery

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
    (issue #945). Setting them unprefixed is what RedBeat finds.

    :param app: The Celery app that Celery Beat runs.
    :returns: None
    """
    # pylint: disable=import-outside-toplevel
    from django.conf import settings

    app.conf.redbeat_redis_url = settings.CELERY_REDBEAT_REDIS_URL
    app.conf.redbeat_redis_options = settings.CELERY_REDBEAT_REDIS_OPTIONS


set_redbeat_conf(APP)

# Load task modules from all registered Django APP configs.
APP.autodiscover_tasks()

APP.conf.broker_connection_retry_on_startup = True
