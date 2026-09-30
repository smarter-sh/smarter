# pylint: disable=W0718,W0613
"""Vectorsearch api/v1/vectorsearch CRUD views."""

from http import HTTPStatus
from typing import Optional

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpResponseNotFound, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.account.models import User, UserProfile
from smarter.apps.vectorsearch.models import (
    Vectorsearch,
)
from smarter.apps.vectorsearch.serializers import (
    VectorsearchSerializer,
)
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAdminAPIView,
    SmarterAdminListAPIView,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.VECTORSEARCH_LOGGING])


###############################################################################
# base views
###############################################################################
class ViewBase(SmarterAdminAPIView):
    """Base class for all vectorsearch detail views."""

    def dispatch(self, request: Request, *args, **kwargs):
        retval = super().dispatch(request, *args, **kwargs)
        if isinstance(request.user, User):
            self.user_profile = get_object_or_404(UserProfile, user=request.user)
            self.account = self.user_profile.cached_account
        return retval


class ListViewBase(SmarterAdminListAPIView):
    """Base class for all vectorsearch list views."""

    def dispatch(self, request: Request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code > 299:
            return response
        self.user_profile = get_object_or_404(UserProfile, user=request.user)
        self.account = self.user_profile.cached_account
        return response


###############################################################################
# Vectorsearch views
###############################################################################


class VectorsearchView(ViewBase):
    """Vectorsearch view for smarter api."""

    serializer_class = VectorsearchSerializer
    vectorsearch: Optional[Vectorsearch] = None
    hashed_id: Optional[str] = None
    vectorsearch_id: Optional[int] = None

    def get_queryset(self, *args, **kwargs):
        return Vectorsearch.objects.filter(id=self.vectorsearch.id)  # type: ignore[return-value]

    def dispatch(self, request: Request, *args, **kwargs):
        self.hashed_id = kwargs.pop("hashed_id", None)
        retval = super().dispatch(request, *args, **kwargs)
        if self.hashed_id:
            self.vectorsearch_id = Vectorsearch.id_from_hashed_id(self.hashed_id)
        else:
            self.vectorsearch_id = kwargs.get("vectorsearch_id")

        if self.vectorsearch_id:
            self.vectorsearch = get_object_or_404(Vectorsearch, pk=self.vectorsearch_id)
            if self.vectorsearch.user_profile and self._user_profile != self.vectorsearch.user_profile:
                self._user_profile = self.vectorsearch.user_profile
                self._account = self.vectorsearch.user_profile.account
                self._user = self.vectorsearch.user_profile.user
                logger.debug(
                    "%s.dispatch() - reinitializing user, account, and user_profile from vectorsearch.user_profile: %s",
                    self.formatted_class_name,
                    self.vectorsearch.user_profile,
                )
            logger.debug("%s.dispatch() - %s %s", self.formatted_class_name, self.vectorsearch, self.user_profile)
        return retval

    def get(self, request: Request, vectorsearch_id: Optional[int] = None):
        if self.vectorsearch:
            serializer = self.serializer_class(self.vectorsearch)
            return Response(serializer.data, status=HTTPStatus.OK)
        return HttpResponseNotFound("Vectorsearch not found")

    def post(self, request: Request, *args, **kwargs):
        try:
            data = request.data
            vectorsearch = Vectorsearch.objects.create(**data)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(vectorsearch.id) + "/")  # type: ignore[return-value]

    def patch(self, request: Request, *args, vectorsearch_id: Optional[int] = None, **kwargs):
        vectorsearch: Optional[Vectorsearch] = None
        data: Optional[dict] = None

        vectorsearch = get_object_or_404(Vectorsearch, pk=vectorsearch_id, account=self.account)

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
                if hasattr(vectorsearch, key):
                    setattr(vectorsearch, key, value)
            vectorsearch.save()
        except ValidationError as e:
            return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        return HttpResponseRedirect(request.path_info)

    def delete(self, request: Request, *args, vectorsearch_id: Optional[int] = None, **kwargs):
        if vectorsearch_id and self.is_superuser():
            vectorsearch = get_object_or_404(Vectorsearch, pk=vectorsearch_id)
        else:
            vectorsearch = self.vectorsearch

        try:
            if vectorsearch:
                vectorsearch.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        plugins_path = request.path_info.rsplit("/", 2)[0]
        return HttpResponseRedirect(plugins_path)


class VectorsearchListView(ListViewBase):
    """Vectorsearch list view for smarter api."""

    serializer_class = VectorsearchSerializer
    vectorsearchs: Optional[QuerySet[Vectorsearch]]

    def dispatch(self, request: Request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code > 299:
            return response
        self.vectorsearchs = Vectorsearch.objects.with_read_permission_for(user=request.user)  # type: ignore[assignment]
        return response

    def get_queryset(self, *args, **kwargs):
        return Vectorsearch.objects.with_read_permission_for(user=self.user)  # type: ignore[return-value]
