# pylint: disable=W0718,W0613
"""
LLMHost api/v1/llmhosts views.

LLMHosts are created and updated by applying manifests, with ``smarter apply``, so these
views do not create or update them:

- ``GET llmhosts/``: the LLMHosts that the user may read.
- ``GET llmhosts/report/``: a summary of the user's LLMHosts: status, GPUs and cost.
- ``GET llmhosts/discover/?q=&task=&catalog=``: search a model catalog, e.g. huggingface or builtin.
- ``GET llmhosts/discover/manifest/?repository=&catalog=&engine=``: draft a manifest for a model.
- ``GET llmhosts/<hashed_id>/``: an LLMHost that the user may read.
- ``DELETE llmhosts/<hashed_id>/``: destroy and delete an LLMHost that the user owns.
- ``GET llmhosts/<hashed_id>/status/``: check an LLMHost's status, now.
- ``GET llmhosts/<hashed_id>/logs/?tail=``: the inference server's recent logs.
- ``GET llmhosts/<hashed_id>/plan/``: the Kubernetes resources that deploy would apply, without secrets.
- ``POST llmhosts/<hashed_id>/deploy/`` and ``POST llmhosts/<hashed_id>/undeploy/``.
"""

from http import HTTPStatus

from django.db.models import QuerySet
from django.http import Http404, JsonResponse
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.llmhost.caching import invalidate_all_cached_llmhosts_for_user_profile
from smarter.apps.llmhost.models import LLMHost
from smarter.apps.llmhost.serializers import LLMHostSerializer
from smarter.apps.llmhost.services import (
    LLMHostClusterError,
    LLMHostDiscoveryError,
    LLMHostService,
    LLMHostServiceError,
)
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
    SmarterAuthenticatedListAPIView,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_HOST_LOGGING])

MAX_DISCOVERY_RESULTS = 50


def service_error(e: LLMHostServiceError) -> JsonResponse:
    """A JSON error response: 503 if the cluster or a catalog is unavailable, else 400."""
    status = (
        HTTPStatus.SERVICE_UNAVAILABLE
        if isinstance(e, (LLMHostClusterError, LLMHostDiscoveryError))
        else HTTPStatus.BAD_REQUEST
    )
    return JsonResponse({"error": str(e)}, status=status)


class LLMHostViewBase(SmarterAuthenticatedAPIView):
    """
    Base class for views of one LLMHost, identified by ``hashed_id`` or ``llmhost_id``.

    :meth:`get_llmhost` returns the LLMHost only if the user may read it, or, with
    ``owner=True``, only if the user owns it. Otherwise it raises :class:`~django.http.Http404`,
    so that the LLMHosts of other accounts are not disclosed.
    """

    service_class = LLMHostService

    def get_llmhost(self, request: Request, owner: bool = False, **kwargs) -> LLMHost:
        """Return the LLMHost in the URL, if the user may read it, or own it."""
        hashed_id = kwargs.get("hashed_id")
        llmhost_id = LLMHost.id_from_hashed_id(hashed_id) if hashed_id else kwargs.get("llmhost_id")
        if not llmhost_id:
            raise Http404("LLMHost not found")
        queryset = (
            LLMHost.objects.with_ownership_permission_for(user=request.user)  # type: ignore[attr-defined]
            if owner
            else LLMHost.objects.with_read_permission_for(user=request.user)  # type: ignore[attr-defined]
        )
        llmhost = queryset.select_related("user_profile__user", "user_profile__account").filter(pk=llmhost_id).first()
        if llmhost is None:
            raise Http404("LLMHost not found")
        return llmhost

    def get_service(self) -> LLMHostService:
        return self.service_class()


class LLMHostView(LLMHostViewBase):
    """Read, or destroy and delete, an LLMHost."""

    serializer_class = LLMHostSerializer

    def get(self, request: Request, *args, **kwargs):
        """Return an LLMHost that the user may read."""
        return Response(LLMHostSerializer(self.get_llmhost(request, **kwargs)).data, status=HTTPStatus.OK)

    def delete(self, request: Request, *args, **kwargs):
        """Destroy the Kubernetes resources of an LLMHost that the user owns, then delete it."""
        llmhost = self.get_llmhost(request, owner=True, **kwargs)
        user_profile = llmhost.user_profile
        try:
            self.get_service().delete(llmhost)
        except LLMHostServiceError as e:
            return service_error(e)
        invalidate_all_cached_llmhosts_for_user_profile(user_profile)
        return Response(status=HTTPStatus.NO_CONTENT)


class LLMHostStatusView(LLMHostViewBase):
    """Check an LLMHost's status, now."""

    def get(self, request: Request, *args, **kwargs):
        llmhost = self.get_llmhost(request, **kwargs)
        observation = self.get_service().observe(llmhost, persist=llmhost.user_profile.user == request.user)
        return JsonResponse({"llmhost": llmhost.name, **observation.to_dict()})


class LLMHostLogsView(LLMHostViewBase):
    """The recent logs of an LLMHost that the user owns."""

    def get(self, request: Request, *args, **kwargs):
        llmhost = self.get_llmhost(request, owner=True, **kwargs)
        try:
            tail = int(request.query_params.get("tail", 200))
        except ValueError:
            return JsonResponse({"error": "tail must be an integer."}, status=HTTPStatus.BAD_REQUEST)
        try:
            logs = self.get_service().logs(llmhost, tail=tail)
        except LLMHostServiceError as e:
            return service_error(e)
        return JsonResponse({"llmhost": llmhost.name, "logs": logs})


class LLMHostPlanView(LLMHostViewBase):
    """The Kubernetes resources that deploy would apply, with secrets redacted."""

    def get(self, request: Request, *args, **kwargs):
        llmhost = self.get_llmhost(request, owner=True, **kwargs)
        try:
            resources = self.get_service().plan(llmhost)
        except LLMHostServiceError as e:
            return service_error(e)
        return JsonResponse({"llmhost": llmhost.name, "resources": resources})


class LLMHostDeployView(LLMHostViewBase):
    """Launch an LLMHost that the user owns."""

    def post(self, request: Request, *args, **kwargs):
        llmhost = self.get_llmhost(request, owner=True, **kwargs)
        try:
            observation = self.get_service().launch(llmhost)
        except LLMHostServiceError as e:
            return service_error(e)
        invalidate_all_cached_llmhosts_for_user_profile(llmhost.user_profile)
        return JsonResponse({"llmhost": llmhost.name, **observation.to_dict()}, status=HTTPStatus.ACCEPTED)


class LLMHostUndeployView(LLMHostViewBase):
    """Destroy the Kubernetes resources of an LLMHost that the user owns.

    ``?purge=true`` also deletes its model volume.
    """

    def post(self, request: Request, *args, **kwargs):
        llmhost = self.get_llmhost(request, owner=True, **kwargs)
        purge = str(request.query_params.get("purge", "false")).lower() == "true"
        try:
            self.get_service().destroy(llmhost, purge=purge)
        except LLMHostServiceError as e:
            return service_error(e)
        invalidate_all_cached_llmhosts_for_user_profile(llmhost.user_profile)
        return JsonResponse({"llmhost": llmhost.name, "status": llmhost.status, "message": llmhost.status_message})


class LLMHostReportView(SmarterAuthenticatedAPIView):
    """A summary of the LLMHosts that the user owns: status, GPUs and cost."""

    def get(self, request: Request, *args, **kwargs):
        llmhosts = LLMHost.objects.with_ownership_permission_for(user=request.user).select_related(  # type: ignore[attr-defined]
            "user_profile__user"
        )
        return JsonResponse(LLMHostService().report(llmhosts.order_by("name")))


class LLMHostDiscoverView(SmarterAuthenticatedAPIView):
    """Search a model catalog: ``?q=``, ``?task=text-generation|embedding``, ``?catalog=huggingface|builtin``, ``?limit=``."""

    def get(self, request: Request, *args, **kwargs):
        params = request.query_params
        try:
            limit = max(1, min(int(params.get("limit", 20)), MAX_DISCOVERY_RESULTS))
        except ValueError:
            return JsonResponse({"error": "limit must be an integer."}, status=HTTPStatus.BAD_REQUEST)
        try:
            models = LLMHostService().search_models(
                query=params.get("q"),
                task=params.get("task"),
                catalog=params.get("catalog", "huggingface"),
                limit=limit,
            )
        except LLMHostServiceError as e:
            return service_error(e)
        return JsonResponse({"models": [model.to_dict() for model in models]})


class LLMHostDiscoverManifestView(SmarterAuthenticatedAPIView):
    """Draft a manifest: ``?repository=`` (required), ``?catalog=``, ``?engine=``, ``?name=``, ``?tokenSecret=``."""

    def get(self, request: Request, *args, **kwargs):
        params = request.query_params
        repository = params.get("repository")
        if not repository:
            return JsonResponse({"error": "repository is required."}, status=HTTPStatus.BAD_REQUEST)
        try:
            manifest = LLMHostService().draft_manifest(
                repository,
                catalog=params.get("catalog", "huggingface"),
                engine=params.get("engine"),
                name=params.get("name"),
                token_secret=params.get("tokenSecret"),
            )
        except LLMHostServiceError as e:
            return service_error(e)
        return JsonResponse({"manifest": manifest})


class LLMHostListView(SmarterAuthenticatedListAPIView):
    """The LLMHosts that the user may read."""

    serializer_class = LLMHostSerializer

    def get_queryset(self, *args, **kwargs) -> QuerySet[LLMHost]:
        return LLMHost.objects.with_read_permission_for(user=self.request.user).order_by("name")  # type: ignore[attr-defined]
