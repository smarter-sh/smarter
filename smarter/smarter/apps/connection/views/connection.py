# pylint: disable=W0613
"""
smarter.apps.connection.views.connection
This module contains views to implement the card-style list view
in the Smarter Dashboard.
"""

from typing import Optional

import yaml
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import render

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.cli.views.describe import ApiV1CliDescribeApiView
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.connection.models import (
    ConnectionBase,
    get_cached_connection_detail_view_and_kind,
)
from smarter.apps.docs.views.base import DocsBaseView
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.helpers.console_helpers import formatted_json
from smarter.common.utils.request import is_authenticated_request
from smarter.lib import logging
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
    SmarterHttpResponseServerError,
)
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CONNECTION_LOGGING])


class ConnectionDetailView(DocsBaseView):
    """
    Renders the detail view for a Smarter dashboard connection.

    This view renders a detailed manifest for a specific connection, including its configuration and metadata, in YAML format. It is intended for authenticated users and provides error handling for missing or unsupported connection kinds and names.

    :param request: Django HTTP request object.
    :type request: WSGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Keyword arguments, must include 'name' (connection name) and 'kind' (connection type).
    :type kwargs: dict

    :returns: Rendered HTML page with connection manifest details, or a 404 error page if the connection is not found or parameters are invalid.
    :rtype: HttpResponse

    .. note::

        The connection name and kind must be provided and valid. Otherwise, a "not found" response is returned.

    .. seealso::

        :class:`ConnectionBase` for connection metadata retrieval.
        :class:`ApiV1CliDescribeApiView` for API details.

    **Example usage**::

        GET /connection/detail/?name=my_connection&kind=custom

    """

    template_path = "common/manifest_detail.html"
    connection: Optional[ConnectionBase] = None

    def get(self, request, *args, **kwargs) -> HttpResponse:
        """
        Handle GET requests to render the connection manifest detail view.
        This method processes the incoming request to retrieve the
        specified connection's manifest details and renders them in a
        user-friendly format. It performs validation on the provided connection
        name and kind, retrieves the connection metadata, and handles any
        errors that may arise during this process.

        Process:
        1. Extract and validate 'name' and 'kind' from kwargs.
        2. Retrieve the connection metadata using the provided name and user context.
        3. If the connection is found, call the API view to get the connection details
        4. Convert the JSON response to YAML format for better readability.
        5. Render the connection manifest detail template with the retrieved data.
        6. Handle any errors that occur during the process and return appropriate error responses.

        :param request: Django HTTP request object.
        :type request: WSGIRequest
        :param args: Additional positional arguments.
        :type args: tuple
        :param kwargs: Keyword arguments, must include 'name' (connection name) and 'kind' (connection type).
        :type kwargs: dict

        :returns: Rendered HTML page with connection manifest details, or an error response if the connection is not found or parameters are invalid.
        :rtype: HttpResponse
        """
        self.name = kwargs.pop("name", None)
        self.kind = SAMKinds.str_to_kind(kwargs.pop("kind", None))
        if self.kind is None:
            logger.error("%s.setup() Connection kind is required but not provided.", self.formatted_class_name)
            return SmarterHttpResponseNotFound(request=request, error_message="Connection kind is required")
        if self.kind not in SAMKinds.all_connections():
            logger.error("%s.setup() Connection kind %s is not supported.", self.formatted_class_name, self.kind)
            return SmarterHttpResponseNotFound(
                request=request, error_message=f"Connection kind {self.kind} is not supported"
            )
        if not self.name:
            logger.error("%s.setup() Connection name is required but not provided.", self.formatted_class_name)
            return SmarterHttpResponseNotFound(request=request, error_message="Connection name is required")
        if not is_authenticated_request(request):
            logger.error("%s.setup() User is not authenticated.", self.formatted_class_name)
            return SmarterHttpResponseNotFound(request=request, error_message="User is not authenticated")
        self.connection = get_cached_connection_detail_view_and_kind(
            user=request.user, kind=self.kind, name=self.name  # type: ignore[arg-type]
        )
        if not self.connection:
            logger.error("%s.post() Connection %s of kind %s not found for user %s.", self.formatted_class_name, self.name, self.kind, request.user.username)  # type: ignore[union-attr]
            return SmarterHttpResponseNotFound(request=request, error_message="Connection not found")

        logger.info(
            "%s.post() Rendering connection detail view for %s of kind %s, kwargs=%s.",
            self.formatted_class_name,
            self.name,
            self.kind,
            kwargs,
        )
        # get_brokered_json_response() adds self.kind to kwargs, so we remove it here.
        # TypeError: smarter.apps.api.v1.cli.views.describe.View.as_view.<locals>.view() got multiple values for keyword argument 'kind'
        kwargs.pop("kind", None)
        kwargs["name"] = self.name
        view = ApiV1CliDescribeApiView.as_view()
        json_response = self.get_brokered_json_response(
            reverse_name=ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.describe,
            view=view,
            request=request,
            *args,
            **kwargs,
        )

        try:
            yaml_response = yaml.dump(json_response, default_flow_style=False)
        except yaml.YAMLError as e:
            logger.error(
                "%s.dispatch() - Error converting JSON response to YAML: %s. JSON response: %s",
                self.formatted_class_name,
                str(e),
                formatted_json(json_response),
            )
            return SmarterHttpResponseServerError(request=request, error_message="Error converting manifest to YAML")

        context = {
            "manifest": yaml_response,
            "page_title": self.name,
        }
        if not self.template_path:
            raise SmarterConfigurationError("self.template_path not set.")

        try:
            response = render(request, self.template_path, context=context)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.dispatch() - Error rendering template: %s. context: %s",
                self.formatted_class_name,
                str(e),
                formatted_json(context),
                exc_info=True,
            )
            return SmarterHttpResponseServerError(request=request, error_message="Error rendering manifest page")
        return response


class ConnectionListView(SmarterAuthenticatedNeverCachedWebView):
    """
    Render the connection list view for the Smarter Workbench web console.

    This view displays all connections available to the authenticated user as cards, providing a summary and quick access to connection details.

    :param request: Django HTTP request object.
    :type request: WSGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    :returns: Rendered HTML page with a card for each connection, or a 404 error page if the user is not authenticated.
    :rtype: HttpResponse

    .. seealso::

        :class:`ConnectionBase` for connection metadata and retrieval.

    **Example usage**::

        GET /connection/list/

    """

    template_path = "connection/connection_list.html"
    connections: list[ConnectionBase]

    def get(self, request: WSGIRequest, *args, **kwargs):
        if request.user is None:
            logger.error("%s.get() Request user is None. This should not happen.", self.formatted_class_name)
            return SmarterHttpResponseNotFound(request=request, error_message="User is not authenticated")
        self.connections = ConnectionBase.get_cached_connections_for_user(request.user)
        context = {
            "connections": self.connections,
        }
        return self.clean_http_response(request=request, template_path=self.template_path, context=context)
