"""
API View for Dashboard for "Service Health" React component.
"""

from http import HTTPStatus

from django.http import JsonResponse
from django.http.request import HttpRequest

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
            "smarter_version": "1.0.0",  # Example value, replace with actual data
            "django_version": "4.2.0",  # Example value, replace with actual data
            "python_version": "3.10.0",  # Example value, replace with actual data
        }
        return JsonResponse(retval, status=HTTPStatus.OK)
