"""
The Connection list page, ``/connection/``, which the single-page console serves (ADR-035).

The console renders ``@smarter/connection-list``'s list at the page's path, and the list calls its list api,
:mod:`smarter.apps.connection.views.listview.api`. The page keeps its view class, named after the list api's, which
:func:`smarter.lib.django.listview.listview_registry` pairs it with, so that the dashboard's global search links to it.
"""

from smarter.apps.dashboard.views.console_app import ConsoleAppView


class ConnectionListView(ConsoleAppView):
    """The Connection list page: the single-page console's, at the path that Django served it at."""
