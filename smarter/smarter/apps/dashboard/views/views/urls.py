"""
URL configuration of the dashboard's page, ``/dashboard/``.

The single-page console serves the dashboard (:class:`~smarter.apps.dashboard.views.console_app.ConsoleAppView`), and
its widgets call the console's dashboard api, ``/api/web/dashboard/``: see :mod:`smarter.apps.dashboard.views.views.api`.
The page keeps its url name, ``dashboard:dashboard``, which the root url's redirect and the sidebar reverse.
"""

from django.urls import path
from django.views.generic.base import RedirectView

from smarter.apps.dashboard.const import namespace
from smarter.apps.dashboard.views.console_app import ConsoleAppView


class DashboardReverseNames:
    """A class to hold the names of the dashboard views for easy reference throughout the codebase."""

    namespace = namespace

    dashboard = namespace


urlpatterns = [
    path("", ConsoleAppView.as_view(), name=DashboardReverseNames.dashboard),
    path("help/", RedirectView.as_view(url="/docs/"), name="help"),
    path("support/", RedirectView.as_view(url="/docs/"), name="support"),
]
