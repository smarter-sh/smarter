# pylint: disable=W0718,W0613
"""Orchestrator api/v1/orchestrator CRUD views."""

from http import HTTPStatus
from typing import Optional

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpResponseNotFound, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.orchestrator.contract.models import OrchestratorApiOrchestrator
from smarter.apps.orchestrator.models import (
    Orchestrator,
)
from smarter.apps.orchestrator.serializers import (
    OrchestratorSerializer,
)
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.contract import ContractListMixin
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAdminAPIView,
    SmarterAdminListAPIView,
)
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ORCHESTRATOR])


###############################################################################
# base views
###############################################################################
class ViewBase(SmarterAdminAPIView):
    """Base class for all orchestrator detail views."""

    # SmarterRequestMixin sets user, user_profile and account from the request,
    # which are immutable once set.


class ListViewBase(SmarterAdminListAPIView):
    """Base class for all orchestrator list views."""

    # SmarterRequestMixin sets user, user_profile and account from the request,
    # which are immutable once set.


###############################################################################
# Orchestrator views
###############################################################################


class OrchestratorView(ViewBase):
    """Orchestrator view for smarter api.

    Its ``GET`` returns an :class:`OrchestratorApiOrchestrator`.
    """

    serializer_class = OrchestratorSerializer
    orchestrator: Optional[Orchestrator] = None
    hashed_id: Optional[str] = None
    orchestrator_id: Optional[int] = None

    def get_queryset(self, *args, **kwargs):
        return Orchestrator.objects.filter(id=self.orchestrator.id)  # type: ignore[return-value]

    def dispatch(self, request: Request, *args, **kwargs):
        self.hashed_id = kwargs.pop("hashed_id", None)
        return super().dispatch(request, *args, **kwargs)

    def initial(self, request: Request, *args, **kwargs):
        """Find the Orchestrator, after DRF has authenticated the request and before the handler runs."""
        super().initial(request, *args, **kwargs)
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
                    "%s.initial() - reinitializing user, account, and user_profile from orchestrator.user_profile: %s",
                    self.formatted_class_name,
                    self.orchestrator.user_profile,
                )
            logger.debug("%s.initial() - %s %s", self.formatted_class_name, self.orchestrator, self.user_profile)

    def get(self, request: Request, orchestrator_id: Optional[int] = None):
        if self.orchestrator:
            return Response(
                OrchestratorApiOrchestrator.from_model(self.orchestrator, request.user).model_dump(mode="json"),
                status=HTTPStatus.OK,
            )
        raise NotFound("Orchestrator not found")

    def post(self, request: Request, *args, **kwargs):
        try:
            data = request.data
            orchestrator = Orchestrator.objects.create(**data)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(orchestrator.id) + "/")  # type: ignore[return-value]

    def patch(self, request: Request, *args, orchestrator_id: Optional[int] = None, **kwargs):
        orchestrator: Optional[Orchestrator] = None
        data: Optional[SmarterDictType] = None

        orchestrator = self.orchestrator
        if not orchestrator:
            return HttpResponseNotFound("Orchestrator not found")

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


class OrchestratorListView(ContractListMixin, ListViewBase):
    """Orchestrator list view for smarter api: :class:`OrchestratorApiOrchestrator` models."""

    serializer_class = OrchestratorSerializer
    contract_model = OrchestratorApiOrchestrator

    def item(self, row):
        """An Orchestrator of the response, whose ``canDelete`` is the requesting user's."""
        return OrchestratorApiOrchestrator.from_model(row, self.request.user).model_dump(mode="json")

    orchestrators: Optional[QuerySet[Orchestrator]]

    def dispatch(self, request: Request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code > 299:
            return response
        self.orchestrators = Orchestrator.objects.with_read_permission_for(user=request.user)  # type: ignore[assignment]
        return response

    def get_queryset(self, *args, **kwargs):
        return (
            Orchestrator.objects.with_read_permission_for(user=self.user)  # type: ignore[return-value]
            .select_related("user_profile__user", "user_profile__account")
            .prefetch_related("tags")
            .order_by("name")
        )
