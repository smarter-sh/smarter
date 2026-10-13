# pylint: disable=W0718,W0613
"""
MCPClient api/v1/mcpclients views.

MCPClients are created and updated by applying manifests, with ``smarter apply``, so
these views do not create or update them. They list, read and delete MCPClients, and
connect to their MCP servers:

- ``GET mcpclients/``: the MCPClients that the user may read.
- ``GET mcpclients/<hashed_id>/``: an MCPClient that the user may read.
- ``DELETE mcpclients/<hashed_id>/``: delete an MCPClient that the user owns.
- ``GET mcpclients/<hashed_id>/tools/``: the tools that the MCPClient offers the LLM,
  from its cached catalog. ``?refresh=true`` reconnects to the server first.
- ``POST mcpclients/<hashed_id>/refresh/``: reconnect to the MCP server, and return the
  MCPClient's status.
- ``POST mcpclients/<hashed_id>/tools/<tool_name>/``: call a tool, with the JSON request
  body as its arguments. Only the owner may call tools.

The responses are built from the models of :mod:`smarter.apps.mcpclient.contract.models`, which the
Smarter api's OpenAPI document publishes. Errors are Django REST framework's ``{"detail": ...}``. A
failed connection to the MCP server adds the MCPClient's connection status beside it.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from http import HTTPStatus
from typing import Optional

from django.db.models import QuerySet
from django.http import Http404
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.mcpclient.caching import (
    get_cached_catalog,
    invalidate_all_cached_mcpclients_for_user_profile,
    invalidate_cached_catalog,
)
from smarter.apps.mcpclient.connection import MCPServerConnection, is_tool_allowed
from smarter.apps.mcpclient.contract.models import (
    MCPClientApiMCPClient,
    MCPClientApiStatus,
    MCPClientApiStatusError,
    MCPClientApiToolResult,
    MCPClientApiTools,
)
from smarter.apps.mcpclient.exceptions import (
    SmarterMCPClientConfigurationError,
    SmarterMCPClientException,
    SmarterMCPClientPermissionError,
)
from smarter.apps.mcpclient.models import MCPClient
from smarter.apps.mcpclient.serializers import MCPClientSerializer
from smarter.apps.mcpclient.signals import mcpclient_called
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.contract import ContractListMixin
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
    SmarterAuthenticatedListAPIView,
)
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPCLIENT_LOGGING])


def status_error(mcpclient: MCPClient, e: SmarterMCPClientException) -> Response:
    """
    The response to a failed connection to an MCPClient's server: the error, beside the MCPClient's connection status.

    :param mcpclient: The MCPClient.
    :type mcpclient: MCPClient
    :param e: The error.
    :type e: SmarterMCPClientException
    :returns: The response, whose status is :func:`error_status`'s.
    :rtype: rest_framework.response.Response
    """
    status = MCPClientApiStatus.from_model(mcpclient)
    error = MCPClientApiStatusError(**status.model_dump(), detail=e.message)
    return Response(error.model_dump(mode="json"), status=error_status(e))


def error_status(e: SmarterMCPClientException) -> int:
    """Return the HTTP status for an MCPClient error."""
    if isinstance(e, SmarterMCPClientPermissionError):
        return HTTPStatus.FORBIDDEN
    if isinstance(e, SmarterMCPClientConfigurationError):
        return HTTPStatus.BAD_REQUEST
    return HTTPStatus.BAD_GATEWAY


class MCPClientViewBase(SmarterAuthenticatedAPIView):
    """
    Base class for views of one MCPClient, identified by ``hashed_id`` or ``mcpclient_id``.

    :meth:`get_mcpclient` returns the MCPClient only if the user may read it, or, with
    ``owner=True``, only if the user owns it. Otherwise it raises :class:`~django.http.Http404`,
    so that the MCPClients of other accounts are not disclosed.
    """

    def mcpclient_id(self, **kwargs) -> Optional[int]:
        """Return the MCPClient id from the URL."""
        hashed_id = kwargs.get("hashed_id")
        if hashed_id:
            return MCPClient.id_from_hashed_id(hashed_id)
        return kwargs.get("mcpclient_id")

    def get_mcpclient(self, request: Request, owner: bool = False, **kwargs) -> MCPClient:
        """
        Return the MCPClient in the URL, if the user may read it, or own it.

        :raises Http404: If the MCPClient does not exist, or the user may not access it.
        """
        mcpclient_id = self.mcpclient_id(**kwargs)
        if not mcpclient_id:
            raise Http404("MCPClient not found")
        queryset = (
            MCPClient.objects.with_ownership_permission_for(user=request.user)  # type: ignore[attr-defined]
            if owner
            else MCPClient.objects.with_read_permission_for(user=request.user)  # type: ignore[attr-defined]
        )
        mcpclient = queryset.select_related("credentials", "user_profile").filter(pk=mcpclient_id).first()
        if mcpclient is None:
            raise Http404("MCPClient not found")
        mcpclient_called.send(sender=self.__class__, mcpclient=mcpclient, request=request, args=(), kwargs=kwargs)
        return mcpclient


class MCPClientView(MCPClientViewBase):
    """Read or delete an MCPClient."""

    serializer_class = MCPClientSerializer

    def get(self, request: Request, *args, **kwargs):
        """Return an MCPClient that the user may read."""
        mcpclient = self.get_mcpclient(request, **kwargs)
        return Response(MCPClientApiMCPClient.from_model(mcpclient, request.user).model_dump(mode="json"))

    def delete(self, request: Request, *args, **kwargs):
        """Delete an MCPClient that the user owns."""
        mcpclient = self.get_mcpclient(request, owner=True, **kwargs)
        user_profile = mcpclient.user_profile
        mcpclient.delete()
        if user_profile:
            invalidate_all_cached_mcpclients_for_user_profile(user_profile)
        return Response(status=HTTPStatus.NO_CONTENT)


class MCPClientToolsView(MCPClientViewBase):
    """The tools that an MCPClient offers the LLM."""

    def get(self, request: Request, *args, **kwargs):
        """Return the MCPClient's allowed tools, from its catalog."""
        mcpclient = self.get_mcpclient(request, **kwargs)
        refresh = str(request.query_params.get("refresh", "false")).lower() == "true"
        try:
            catalog = get_cached_catalog(mcpclient, refresh=refresh)
        except SmarterMCPClientException as e:
            return status_error(mcpclient, e)
        tools = [tool for tool in catalog.tools if is_tool_allowed(mcpclient, tool.name)]
        return Response(MCPClientApiTools.from_catalog(mcpclient, catalog, tools).model_dump(mode="json"))


class MCPClientRefreshView(MCPClientViewBase):
    """Reconnect to an MCPClient's MCP server."""

    def post(self, request: Request, *args, **kwargs):
        """Reconnect to the MCP server, and return the MCPClient's status."""
        mcpclient = self.get_mcpclient(request, owner=True, **kwargs)
        invalidate_cached_catalog(mcpclient)
        try:
            get_cached_catalog(mcpclient, refresh=True)
        except SmarterMCPClientException as e:
            return status_error(mcpclient, e)
        return Response(MCPClientApiStatus.from_model(mcpclient).model_dump(mode="json"))


class MCPClientToolCallView(MCPClientViewBase):
    """Call one of an MCPClient's tools.

    Only the owner may call tools.
    """

    def post(self, request: Request, *args, **kwargs):
        """Call the tool, with the JSON request body as its arguments."""
        mcpclient = self.get_mcpclient(request, owner=True, **kwargs)
        tool_name = kwargs.get("tool_name", "")
        arguments = request.data if isinstance(request.data, dict) else {}
        try:
            result = MCPServerConnection(mcpclient).call_tool(tool_name, arguments)
        except SmarterMCPClientException as e:
            return Response({"detail": e.message}, status=error_status(e))
        return Response(MCPClientApiToolResult.from_result(mcpclient, tool_name, result).model_dump(mode="json"))


class MCPClientListView(ContractListMixin, SmarterAuthenticatedListAPIView):
    """The MCPClients that the user may read."""

    serializer_class = MCPClientSerializer
    contract_model = MCPClientApiMCPClient

    def item(self, row):
        """An MCPClient of the response, whose ``canDelete`` is the requesting user's."""
        return MCPClientApiMCPClient.from_model(row, self.request.user).model_dump(mode="json")

    def get_queryset(self, *args, **kwargs) -> QuerySet[MCPClient]:
        return MCPClient.objects.with_read_permission_for(user=self.request.user).order_by("name")  # type: ignore[attr-defined]
