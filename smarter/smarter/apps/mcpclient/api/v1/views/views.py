# pylint: disable=W0718,W0613
"""MCPClient api/v1/mcpclient CRUD views."""

from http import HTTPStatus
from typing import Optional

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpResponseNotFound, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.account.models import User, UserProfile
from smarter.apps.mcpclient.models import (
    MCPClient,
)
from smarter.apps.mcpclient.serializers import (
    MCPClientSerializer,
)
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAdminAPIView,
    SmarterAdminListAPIView,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPCLIENT_LOGGING])


###############################################################################
# base views
###############################################################################
class ViewBase(SmarterAdminAPIView):
    """Base class for all mcpclient detail views."""

    def dispatch(self, request: Request, *args, **kwargs):
        retval = super().dispatch(request, *args, **kwargs)
        if isinstance(request.user, User):
            self.user_profile = get_object_or_404(UserProfile, user=request.user)
            self.account = self.user_profile.cached_account
        return retval


class ListViewBase(SmarterAdminListAPIView):
    """Base class for all mcpclient list views."""

    def dispatch(self, request: Request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code > 299:
            return response
        self.user_profile = get_object_or_404(UserProfile, user=request.user)
        self.account = self.user_profile.cached_account
        return response


###############################################################################
# MCPClient views
###############################################################################


class MCPClientView(ViewBase):
    """MCPClient view for smarter api."""

    serializer_class = MCPClientSerializer
    mcpclient: Optional[MCPClient] = None
    hashed_id: Optional[str] = None
    mcpclient_id: Optional[int] = None

    def get_queryset(self, *args, **kwargs):
        return MCPClient.objects.filter(id=self.mcpclient.id)  # type: ignore[return-value]

    def dispatch(self, request: Request, *args, **kwargs):
        self.hashed_id = kwargs.pop("hashed_id", None)
        retval = super().dispatch(request, *args, **kwargs)
        if self.hashed_id:
            self.mcpclient_id = MCPClient.id_from_hashed_id(self.hashed_id)
        else:
            self.mcpclient_id = kwargs.get("mcpclient_id")

        if self.mcpclient_id:
            self.mcpclient = get_object_or_404(MCPClient, pk=self.mcpclient_id)
            if self.mcpclient.user_profile and self._user_profile != self.mcpclient.user_profile:
                self._user_profile = self.mcpclient.user_profile
                self._account = self.mcpclient.user_profile.account
                self._user = self.mcpclient.user_profile.user
                logger.debug(
                    "%s.dispatch() - reinitializing user, account, and user_profile from mcpclient.user_profile: %s",
                    self.formatted_class_name,
                    self.mcpclient.user_profile,
                )
            logger.debug("%s.dispatch() - %s %s", self.formatted_class_name, self.mcpclient, self.user_profile)
        return retval

    def get(self, request: Request, mcpclient_id: Optional[int] = None):
        if self.mcpclient:
            serializer = self.serializer_class(self.mcpclient)
            return Response(serializer.data, status=HTTPStatus.OK)
        return HttpResponseNotFound("MCPClient not found")

    def post(self, request: Request, *args, **kwargs):
        try:
            data = request.data
            mcpclient = MCPClient.objects.create(**data)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(mcpclient.id) + "/")  # type: ignore[return-value]

    def patch(self, request: Request, *args, mcpclient_id: Optional[int] = None, **kwargs):
        mcpclient: Optional[MCPClient] = None
        data: Optional[dict] = None

        mcpclient = get_object_or_404(MCPClient, pk=mcpclient_id, account=self.account)

        try:
            data = request.data
            if not isinstance(data, dict):
                return JsonResponse(
                    {"error": f"Invalid request data. Expected a JSON dict in request body but received {type(data)}"},
                    status=HTTPStatus.BAD_REQUEST,
                )
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)

        try:
            for key, value in data.items():
                if hasattr(mcpclient, key):
                    setattr(mcpclient, key, value)
            mcpclient.save()
        except ValidationError as e:
            return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        return HttpResponseRedirect(request.path_info)

    def delete(self, request: Request, *args, mcpclient_id: Optional[int] = None, **kwargs):
        if mcpclient_id and self.is_superuser():
            mcpclient = get_object_or_404(MCPClient, pk=mcpclient_id)
        else:
            mcpclient = self.mcpclient

        try:
            if mcpclient:
                mcpclient.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        plugins_path = request.path_info.rsplit("/", 2)[0]
        return HttpResponseRedirect(plugins_path)


class MCPClientListView(ListViewBase):
    """MCPClient list view for smarter api."""

    serializer_class = MCPClientSerializer
    mcpclients: Optional[QuerySet[MCPClient]]

    def dispatch(self, request: Request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code > 299:
            return response
        self.mcpclients = MCPClient.objects.with_read_permission_for(user=request.user)  # type: ignore[assignment]
        return response

    def get_queryset(self, *args, **kwargs):
        return MCPClient.objects.with_read_permission_for(user=self.user)  # type: ignore[return-value]
