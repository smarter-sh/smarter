"""
API View for Dashboard for "Service Health" React component.
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
    API view for the "Service Health" React component on the dashboard.
    """

    def post(self, request: HttpRequest, *args, **kwargs):

        retval = {
            "smarter_version": smarter_settings.version,
            "linux_distribution": smarter_settings.linux_distribution,
            "django_version": smarter_settings.django_version,
            "python_version": smarter_settings.python_version,
            "pydantic_version": smarter_settings.pydantic_version,
            "drf_version": smarter_settings.drf_version,
        }
        return JsonResponse(retval, status=HTTPStatus.OK)
