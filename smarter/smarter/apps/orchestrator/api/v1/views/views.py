# pylint: disable=W0718,W0613
"""Orchestrator api/v1/orchestrator CRUD views."""

from http import HTTPStatus
from typing import Optional

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpResponseNotFound, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.account.models import User, UserProfile
from smarter.apps.orchestrator.models import (
    Orchestrator,
)
from smarter.apps.orchestrator.serializers import (
    OrchestratorSerializer,
)
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAdminAPIView,
    SmarterAdminListAPIView,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ORCHESTRATOR])


###############################################################################
# base views
###############################################################################
class ViewBase(SmarterAdminAPIView):
    """Base class for all orchestrator detail views."""

    def dispatch(self, request: Request, *args, **kwargs):
        retval = super().dispatch(request, *args, **kwargs)
        if isinstance(request.user, User):
            self.user_profile = get_object_or_404(UserProfile, user=request.user)
            self.account = self.user_profile.cached_account
        return retval


class ListViewBase(SmarterAdminListAPIView):
    """Base class for all orchestrator list views."""

    def dispatch(self, request: Request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code > 299:
            return response
        self.user_profile = get_object_or_404(UserProfile, user=request.user)
        self.account = self.user_profile.cached_account
        return response


###############################################################################
# Orchestrator views
###############################################################################


class OrchestratorView(ViewBase):
    """Orchestrator view for smarter api."""

    serializer_class = OrchestratorSerializer
    orchestrator: Optional[Orchestrator] = None
    hashed_id: Optional[str] = None
    orchestrator_id: Optional[int] = None

    def get_queryset(self, *args, **kwargs):
        return Orchestrator.objects.filter(id=self.orchestrator.id)  # type: ignore[return-value]

    def dispatch(self, request: Request, *args, **kwargs):
        self.hashed_id = kwargs.pop("hashed_id", None)
        retval = super().dispatch(request, *args, **kwargs)
        if self.hashed_id:
            self.orchestrator_id = Orchestrator.id_from_hashed_id(self.hashed_id)
        else:
            self.orchestrator_id = kwargs.get("orchestrator_id")

        if self.orchestrator_id:
            self.orchestrator = get_object_or_404(Orchestrator, pk=self.orchestrator_id)
            if self.orchestrator.user_profile and self._user_profile != self.orchestrator.user_profile:
                self._user_profile = self.orchestrator.user_profile
                self._account = self.orchestrator.user_profile.account
                self._user = self.orchestrator.user_profile.user
                logger.debug(
                    "%s.dispatch() - reinitializing user, account, and user_profile from orchestrator.user_profile: %s",
                    self.formatted_class_name,
                    self.orchestrator.user_profile,
                )
            logger.debug("%s.dispatch() - %s %s", self.formatted_class_name, self.orchestrator, self.user_profile)
        return retval

    def get(self, request: Request, orchestrator_id: Optional[int] = None):
        if self.orchestrator:
            serializer = self.serializer_class(self.orchestrator)
            return Response(serializer.data, status=HTTPStatus.OK)
        return HttpResponseNotFound("Orchestrator not found")

    def post(self, request: Request, *args, **kwargs):
        try:
            data = request.data
            orchestrator = Orchestrator.objects.create(**data)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(orchestrator.id) + "/")  # type: ignore[return-value]

    def patch(self, request: Request, *args, orchestrator_id: Optional[int] = None, **kwargs):
        orchestrator: Optional[Orchestrator] = None
        data: Optional[dict] = None

        orchestrator = get_object_or_404(Orchestrator, pk=orchestrator_id, account=self.account)

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
                if hasattr(orchestrator, key):
                    setattr(orchestrator, key, value)
            orchestrator.save()
        except ValidationError as e:
            return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        return HttpResponseRedirect(request.path_info)

    def delete(self, request: Request, *args, orchestrator_id: Optional[int] = None, **kwargs):
        if orchestrator_id and self.is_superuser():
            orchestrator = get_object_or_404(Orchestrator, pk=orchestrator_id)
        else:
            orchestrator = self.orchestrator

        try:
            if orchestrator:
                orchestrator.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        plugins_path = request.path_info.rsplit("/", 2)[0]
        return HttpResponseRedirect(plugins_path)


class OrchestratorListView(ListViewBase):
    """Orchestrator list view for smarter api."""

    serializer_class = OrchestratorSerializer
    orchestrators: Optional[QuerySet[Orchestrator]]

    def dispatch(self, request: Request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code > 299:
            return response
        self.orchestrators = Orchestrator.objects.with_read_permission_for(user=request.user)  # type: ignore[assignment]
        return response

    def get_queryset(self, *args, **kwargs):
        return Orchestrator.objects.with_read_permission_for(user=self.user)  # type: ignore[return-value]
