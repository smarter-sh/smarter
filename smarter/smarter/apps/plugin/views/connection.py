"""
smarter.apps.plugin.views.connection
This module contains views to implement the card-style list view
in the Smarter Dashboard.
"""

import logging

from django.core.handlers.wsgi import WSGIRequest

from smarter.apps.plugin.models import ConnectionBase
from smarter.lib.django.http.shortcuts import SmarterHttpResponseNotFound
from smarter.lib.django.view_helpers import SmarterAuthenticatedNeverCachedWebView


logger = logging.getLogger(__name__)


class ConnectionListView(SmarterAuthenticatedNeverCachedWebView):
    """
    list view for smarter workbench web console. It generates cards for each
    Connection.
    """

    template_path = "plugin/connections_list.html"
    connections: list[ConnectionBase]

    def setup(self, request: WSGIRequest, *args, **kwargs):
        self.connections = ConnectionBase.get_cached_connections_for_user(self.user)


class ConnectionDetailView(SmarterAuthenticatedNeverCachedWebView):
    """
    detail view for Smarter dashboard.
    """

    template_path = "plugin/plugin_detail.html"
    name: str = None
    kind: str = None
    connection: ConnectionBase = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.name = kwargs.pop("name", None)
        self.kind = kwargs.pop("kind", None)
        self.connection = ConnectionBase.get_cached_connection_by_name_and_kind(
            user=self.user, kind=self.kind, name=self.name
        )

    def dispatch(self, request, *args, **kwargs):
        if not self.connection:
            return SmarterHttpResponseNotFound("Connection not found")
        return super().dispatch(request, *args, **kwargs)
