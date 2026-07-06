# pylint: disable=W0718,W0613
"""Guardrail api/v1/guardrail CRUD views."""

from http import HTTPStatus
from typing import Optional

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpResponseNotFound, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.account.models import User, UserProfile
from smarter.apps.guardrail.models import (
    Guardrail,
)
from smarter.apps.guardrail.serializers import (
    GuardrailSerializer,
)
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAdminAPIView,
    SmarterAdminListAPIView,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.GUARDRAIL_LOGGING])


###############################################################################
# base views
###############################################################################
class ViewBase(SmarterAdminAPIView):
    """Base class for all guardrail detail views."""

    def dispatch(self, request: Request, *args, **kwargs):
        retval = super().dispatch(request, *args, **kwargs)
        if isinstance(request.user, User):
            self.user_profile = get_object_or_404(UserProfile, user=request.user)
            self.account = self.user_profile.cached_account
        return retval


class ListViewBase(SmarterAdminListAPIView):
    """Base class for all guardrail list views."""

    def dispatch(self, request: Request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code > 299:
            return response
        self.user_profile = get_object_or_404(UserProfile, user=request.user)
        self.account = self.user_profile.cached_account
        return response


###############################################################################
# Guardrail views
###############################################################################


class GuardrailView(ViewBase):
    """Guardrail view for smarter api."""

    serializer_class = GuardrailSerializer
    guardrail: Optional[Guardrail] = None
    hashed_id: Optional[str] = None
    guardrail_id: Optional[int] = None

    def get_queryset(self, *args, **kwargs):
        return Guardrail.objects.filter(id=self.guardrail.id)  # type: ignore[return-value]

    def dispatch(self, request: Request, *args, **kwargs):
        self.hashed_id = kwargs.pop("hashed_id", None)
        retval = super().dispatch(request, *args, **kwargs)
        if self.hashed_id:
            self.guardrail_id = Guardrail.id_from_hashed_id(self.hashed_id)
        else:
            self.guardrail_id = kwargs.get("guardrail_id")

        if self.guardrail_id:
            self.guardrail = get_object_or_404(Guardrail, pk=self.guardrail_id)
            if self.guardrail.user_profile and self._user_profile != self.guardrail.user_profile:
                self._user_profile = self.guardrail.user_profile
                self._account = self.guardrail.user_profile.account
                self._user = self.guardrail.user_profile.user
                logger.debug(
                    "%s.dispatch() - reinitializing user, account, and user_profile from guardrail.user_profile: %s",
                    self.formatted_class_name,
                    self.guardrail.user_profile,
                )
            logger.debug("%s.dispatch() - %s %s", self.formatted_class_name, self.guardrail, self.user_profile)
        return retval

    def get(self, request: Request, guardrail_id: Optional[int] = None):
        if self.guardrail:
            serializer = self.serializer_class(self.guardrail)
            return Response(serializer.data, status=HTTPStatus.OK)
        return HttpResponseNotFound("Guardrail not found")

    def post(self, request: Request, *args, **kwargs):
        try:
            data = request.data
            guardrail = Guardrail.objects.create(**data)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(guardrail.id) + "/")  # type: ignore[return-value]

    def patch(self, request: Request, *args, guardrail_id: Optional[int] = None, **kwargs):
        guardrail: Optional[Guardrail] = None
        data: Optional[dict] = None

        guardrail = get_object_or_404(Guardrail, pk=guardrail_id, account=self.account)

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
                if hasattr(guardrail, key):
                    setattr(guardrail, key, value)
            guardrail.save()
        except ValidationError as e:
            return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        return HttpResponseRedirect(request.path_info)

    def delete(self, request: Request, *args, guardrail_id: Optional[int] = None, **kwargs):
        if guardrail_id and self.is_superuser():
            guardrail = get_object_or_404(Guardrail, pk=guardrail_id)
        else:
            guardrail = self.guardrail

        try:
            if guardrail:
                guardrail.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        plugins_path = request.path_info.rsplit("/", 2)[0]
        return HttpResponseRedirect(plugins_path)


class GuardrailListView(ListViewBase):
    """Guardrail list view for smarter api."""

    serializer_class = GuardrailSerializer
    guardrails: Optional[QuerySet[Guardrail]]

    def dispatch(self, request: Request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code > 299:
            return response
        self.guardrails = Guardrail.objects.with_read_permission_for(user=request.user)  # type: ignore[assignment]
        return response

    def get_queryset(self, *args, **kwargs):
        return Guardrail.objects.with_read_permission_for(user=self.user)  # type: ignore[return-value]
