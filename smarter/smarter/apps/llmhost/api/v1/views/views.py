# pylint: disable=W0718,W0613
"""LLMHost api/v1/llmhost CRUD views."""

from http import HTTPStatus
from typing import Optional

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpResponseNotFound, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.account.models import User, UserProfile
from smarter.apps.llmhost.models import (
    LLMHost,
)
from smarter.apps.llmhost.serializers import (
    LLMHostSerializer,
)
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAdminAPIView,
    SmarterAdminListAPIView,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_HOST_LOGGING])


###############################################################################
# base views
###############################################################################
class ViewBase(SmarterAdminAPIView):
    """Base class for all llmhost detail views."""

    def dispatch(self, request: Request, *args, **kwargs):
        retval = super().dispatch(request, *args, **kwargs)
        if isinstance(request.user, User):
            self.user_profile = get_object_or_404(UserProfile, user=request.user)
            self.account = self.user_profile.cached_account
        return retval


class ListViewBase(SmarterAdminListAPIView):
    """Base class for all llmhost list views."""

    def dispatch(self, request: Request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code > 299:
            return response
        self.user_profile = get_object_or_404(UserProfile, user=request.user)
        self.account = self.user_profile.cached_account
        return response


###############################################################################
# LLMHost views
###############################################################################


class LLMHostView(ViewBase):
    """LLMHost view for smarter api."""

    serializer_class = LLMHostSerializer
    llmhost: Optional[LLMHost] = None
    hashed_id: Optional[str] = None
    llmhost_id: Optional[int] = None

    def get_queryset(self, *args, **kwargs):
        return LLMHost.objects.filter(id=self.llmhost.id)  # type: ignore[return-value]

    def dispatch(self, request: Request, *args, **kwargs):
        self.hashed_id = kwargs.pop("hashed_id", None)
        retval = super().dispatch(request, *args, **kwargs)
        if self.hashed_id:
            self.llmhost_id = LLMHost.id_from_hashed_id(self.hashed_id)
        else:
            self.llmhost_id = kwargs.get("llmhost_id")

        if self.llmhost_id:
            self.llmhost = get_object_or_404(LLMHost, pk=self.llmhost_id)
            if self.llmhost.user_profile and self._user_profile != self.llmhost.user_profile:
                self._user_profile = self.llmhost.user_profile
                self._account = self.llmhost.user_profile.account
                self._user = self.llmhost.user_profile.user
                logger.debug(
                    "%s.dispatch() - reinitializing user, account, and user_profile from llmhost.user_profile: %s",
                    self.formatted_class_name,
                    self.llmhost.user_profile,
                )
            logger.debug("%s.dispatch() - %s %s", self.formatted_class_name, self.llmhost, self.user_profile)
        return retval

    def get(self, request: Request, llmhost_id: Optional[int] = None):
        if self.llmhost:
            serializer = self.serializer_class(self.llmhost)
            return Response(serializer.data, status=HTTPStatus.OK)
        return HttpResponseNotFound("LLMHost not found")

    def post(self, request: Request, *args, **kwargs):
        try:
            data = request.data
            llmhost = LLMHost.objects.create(**data)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(llmhost.id) + "/")  # type: ignore[return-value]

    def patch(self, request: Request, *args, llmhost_id: Optional[int] = None, **kwargs):
        llmhost: Optional[LLMHost] = None
        data: Optional[dict] = None

        llmhost = get_object_or_404(LLMHost, pk=llmhost_id, account=self.account)

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
                if hasattr(llmhost, key):
                    setattr(llmhost, key, value)
            llmhost.save()
        except ValidationError as e:
            return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        return HttpResponseRedirect(request.path_info)

    def delete(self, request: Request, *args, llmhost_id: Optional[int] = None, **kwargs):
        if llmhost_id and self.is_superuser():
            llmhost = get_object_or_404(LLMHost, pk=llmhost_id)
        else:
            llmhost = self.llmhost

        try:
            if llmhost:
                llmhost.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        plugins_path = request.path_info.rsplit("/", 2)[0]
        return HttpResponseRedirect(plugins_path)


class LLMHostListView(ListViewBase):
    """LLMHost list view for smarter api."""

    serializer_class = LLMHostSerializer
    llmhosts: Optional[QuerySet[LLMHost]]

    def dispatch(self, request: Request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code > 299:
            return response
        self.llmhosts = LLMHost.objects.with_read_permission_for(user=request.user)  # type: ignore[assignment]
        return response

    def get_queryset(self, *args, **kwargs):
        return LLMHost.objects.with_read_permission_for(user=self.user)  # type: ignore[return-value]
