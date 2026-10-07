"""
API view for the Dashboard "Service Health" React component.

This module provides a lightweight JSON endpoint consumed by the Service Health
React widget on the main dashboard page. It returns version and environment
metadata for the running Smarter platform so that operators can quickly verify
which versions of core dependencies are active, along with the results of live
checks of the backing services: the database, the cache, the Celery task broker,
and the Celery workers.

Classes:
    ServiceHealthView: Authenticated POST endpoint that returns platform
        version and environment metadata as a JSON response.

Example:
    Wire up the view in your URL configuration::

        from smarter.apps.dashboard.views.views.api.service_health import ServiceHealthView

        urlpatterns = [
            path("service-health/", ServiceHealthView.as_view(), name="service_health"),
        ]
"""

from http import HTTPStatus
from typing import Callable
from uuid import uuid4

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.http.request import HttpRequest

from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.views import (
    SmarterAuthenticatedWebView,
)

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)

CELERY_PING_TIMEOUT = 0.5  # seconds. the widget loads asynchronously, but should not hang.


def check_database() -> bool:
    """True if the database answers a trivial query."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        return cursor.fetchone() == (1,)


def check_cache() -> bool:
    """True if a value written to the cache can be read back."""
    key = f"smarter_service_health_{uuid4().hex}"
    cache.set(key, "ok", timeout=10)
    try:
        return cache.get(key) == "ok"
    finally:
        cache.delete(key)


def check_task_broker() -> bool:
    """True if the Celery broker accepts a connection."""
    # pylint: disable=C0415
    from smarter.lib.celery_conf import APP

    with APP.connection_for_read() as conn:
        conn.ensure_connection(max_retries=1)
    return True


def check_workers() -> bool:
    """True if at least one Celery worker answers a ping."""
    # pylint: disable=C0415
    from smarter.lib.celery_conf import APP

    return bool(APP.control.ping(timeout=CELERY_PING_TIMEOUT))


HEALTH_CHECKS: dict[str, Callable[[], bool]] = {
    "Database": check_database,
    "Cache": check_cache,
    "Task Broker": check_task_broker,
    "Workers": check_workers,
}


def run_health_checks() -> list[dict[str, object]]:
    """Run each health check, and report a failure, or an exception, as unhealthy."""
    retval = []
    for name, check in HEALTH_CHECKS.items():
        try:
            healthy = bool(check())
        # pylint: disable=broad-except
        except Exception as e:
            logger.warning("%s health check %s failed: %s", logger_prefix, name, e)
            healthy = False
        retval.append({"name": name, "healthy": healthy})
    return retval


# pylint: disable=W0613
class ServiceHealthView(SmarterAuthenticatedWebView):
    """
    Authenticated JSON API view that reports platform version and environment metadata.

    Extends :class:`~smarter.lib.django.views.SmarterAuthenticatedWebView` to
    restrict access to authenticated users.

    On a ``POST`` request the view reads version strings and environment
    information from :data:`~smarter.common.conf.smarter_settings`, runs the
    live :data:`HEALTH_CHECKS`, and returns them as a JSON object with an HTTP
    200 status. ``health_score`` is the percentage of checks that passed.

    Response shape:

    .. code-block:: json

        {
            "smarter_version": "1.2.3",
            "linux_distribution": "Ubuntu 22.04",
            "django_version": "4.2.0",
            "python_version": "3.11.0",
            "pydantic_version": "2.0.0",
            "drf_version": "3.14.0",
            "health_checks": [
                {"name": "Database", "healthy": true},
                {"name": "Cache", "healthy": true},
                {"name": "Task Broker", "healthy": true},
                {"name": "Workers", "healthy": false}
            ],
            "health_score": 75
        }
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns the class name in a formatted string along with the name of this view."""
        class_name = f"{__name__}.{ServiceHealthView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to return platform health metadata.

        :param request: The incoming HTTP POST request from the client.
        :type request: django.http.HttpRequest
        :param args: Additional positional arguments forwarded by the URL dispatcher.
        :param kwargs: Additional keyword arguments forwarded by the URL dispatcher.
        :returns: A JSON response containing platform version and environment metadata,
            and the results of the health checks.
        :rtype: django.http.JsonResponse
        """

        health_checks = run_health_checks()
        healthy = sum(1 for check in health_checks if check["healthy"])
        retval = {
            "smarter_version": smarter_settings.version,
            "linux_distribution": smarter_settings.linux_distribution,
            "django_version": smarter_settings.django_version,
            "python_version": smarter_settings.python_version,
            "pydantic_version": smarter_settings.pydantic_version,
            "drf_version": smarter_settings.drf_version,
            "health_checks": health_checks,
            "health_score": round(healthy / len(health_checks) * 100),
        }
        return JsonResponse(retval, status=HTTPStatus.OK)
