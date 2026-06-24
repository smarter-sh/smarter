"""
URL configuration for the dashboard application.

This module is the top-level URL router for the ``smarter.apps.dashboard``
application. It includes the URL configurations from each dashboard
sub-application and mounts them at the paths listed below.

Attributes:
    app_name (str): The Django application namespace, taken from
        :data:`smarter.apps.dashboard.const.namespace`.

Example:
    Include these URLs from the project-level URL configuration::

        from django.urls import include, path

        urlpatterns = [
            path("dashboard/", include("smarter.apps.dashboard.urls")),
        ]
"""

from django.urls import include, path

from smarter.apps.dashboard.const import namespace
from smarter.apps.dashboard.views.passthrough import urls as passthrough_urls
from smarter.apps.dashboard.views.profile import urls as profile_urls
from smarter.apps.dashboard.views.terminal_emulator import urls as logs_urls
from smarter.apps.dashboard.views.views import urls as dashboard_urls
from smarter.lib import logging

logger = logging.getLogger(__name__)

app_name = namespace


urlpatterns = [
    path("", include(dashboard_urls)),
    path("logs/", include(logs_urls, namespace=logs_urls.app_name)),
    path("passthrough/", include(passthrough_urls, namespace=passthrough_urls.app_name)),
    path("profile/", include(profile_urls, namespace=profile_urls.app_name)),
]
