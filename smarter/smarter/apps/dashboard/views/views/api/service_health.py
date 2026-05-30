"""
API view for the Dashboard "Service Health" React component.

This module provides a lightweight JSON endpoint consumed by the Service Health
React widget on the main dashboard page. It returns version and environment
metadata for the running Smarter platform so that operators can quickly verify
which versions of core dependencies are active.

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

from django.http import JsonResponse
from django.http.request import HttpRequest

from smarter.common.conf import smarter_settings
from smarter.lib.django.views import (
    SmarterAuthenticatedWebView,
)


# pylint: disable=W0613
class ServiceHealthView(SmarterAuthenticatedWebView):
    """
    Authenticated JSON API view that reports platform version and environment metadata.

    Extends :class:`~smarter.lib.django.views.SmarterAuthenticatedWebView` to
    restrict access to authenticated users.

    On a ``POST`` request the view reads version strings and environment
    information from :data:`~smarter.common.conf.smarter_settings` and returns
    them as a flat JSON object with an HTTP 200 status.

    Response shape:

    .. code-block:: json

        {
            "smarter_version": "1.2.3",
            "linux_distribution": "Ubuntu 22.04",
            "django_version": "4.2.0",
            "python_version": "3.11.0",
            "pydantic_version": "2.0.0",
            "drf_version": "3.14.0"
        }
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to return platform health metadata.
        :param request: The incoming HTTP POST request from the client.
        :type request: django.http.HttpRequest
        :param args: Additional positional arguments forwarded by the URL dispatcher.
        :param kwargs: Additional keyword arguments forwarded by the URL dispatcher.
        :returns: A JSON response containing platform version and environment metadata.
        :rtype: django.http.JsonResponse
        """

        retval = {
            "smarter_version": smarter_settings.version,
            "linux_distribution": smarter_settings.linux_distribution,
            "django_version": smarter_settings.django_version,
            "python_version": smarter_settings.python_version,
            "pydantic_version": smarter_settings.pydantic_version,
            "drf_version": smarter_settings.drf_version,
        }
        return JsonResponse(retval, status=HTTPStatus.OK)
