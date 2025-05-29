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


class ConnectionDetailView(SmarterAuthenticatedNeverCachedWebView):
    """
    detail view for Smarter dashboard.
    """

    template_path = "plugin/connection_detail.html"
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

    def get(self, request, *args, **kwargs):
        if not self.connection:
            return SmarterHttpResponseNotFound(request=request, error_message="Connection not found")
        context = {}
        return self.clean_http_response(request=request, template_path=self.template_path, context=context)


class ConnectionListView(SmarterAuthenticatedNeverCachedWebView):
    """
    list view for smarter workbench web console. It generates cards for each
    Connection.
    """

    template_path = "plugin/connection_list.html"
    connections: list[ConnectionBase]

    def get(self, request: WSGIRequest, *args, **kwargs):
        logger.info("Fetching connections for user: %s", self.user.username)
        self.connections = ConnectionBase.get_cached_connections_for_user(self.user)
        if not self.connections:
            logger.warning("No connections found for user: %s", self.user.username)
            return SmarterHttpResponseNotFound(request=request, error_message="No connections found")
        context = {}
        logger.info("rendering page connections for user: %s", self.user.username)
        return self.clean_http_response(request=request, template_path=self.template_path, context=context)
