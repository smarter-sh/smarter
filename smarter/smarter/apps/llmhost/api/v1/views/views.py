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

The responses are built from the models of :mod:`smarter.apps.llmhost.contract.models`, which the
Smarter api's OpenAPI document publishes. Errors are Django REST framework's ``{"detail": ...}``.
"""

from http import HTTPStatus

from django.db.models import QuerySet
from django.http import Http404
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.llmhost.caching import invalidate_all_cached_llmhosts_for_user_profile
from smarter.apps.llmhost.contract.models import (
    LLMHostApiCatalogModel,
    LLMHostApiDiscovery,
    LLMHostApiDraftManifest,
    LLMHostApiLLMHost,
    LLMHostApiLogs,
    LLMHostApiObservation,
    LLMHostApiPlan,
    LLMHostApiStatus,
    LLMHostApiUndeployed,
)
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
from smarter.lib.drf.views.contract import ContractListMixin
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
    SmarterAuthenticatedListAPIView,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_HOST_LOGGING])

MAX_DISCOVERY_RESULTS = 50


def error(message: str, status: int = HTTPStatus.BAD_REQUEST) -> Response:
    """
    An error response: Django REST framework's ``{"detail": ...}``, as every error of the REST api.

    :param message: The error's detail.
    :param status: The HTTP status.
    :returns: The response.
    """
    return Response({"detail": message}, status=status)


def service_error(e: LLMHostServiceError) -> Response:
    """
    An error response: 503 if the cluster or a catalog is unavailable, else 400.

    :param e: The service's error.
    :returns: The response, whose detail is the error's message.
    """
    status = HTTPStatus.BAD_REQUEST
    if isinstance(e, (LLMHostClusterError, LLMHostDiscoveryError)):
        status = HTTPStatus.SERVICE_UNAVAILABLE
    return error(str(e), status)


def host_status(llmhost: LLMHost, observation, status: int = HTTPStatus.OK) -> Response:
    """
    The response of a status check or a deployment: the observation, with the LLMHost's name.

    :param llmhost: The LLMHost.
    :param observation: Its :class:`~smarter.apps.llmhost.services.observability.LLMHostObservation`.
    :param status: The HTTP status.
    :returns: The response.
    """
    api_observation = LLMHostApiObservation.from_observation(observation)
    response = LLMHostApiStatus(llmhost=llmhost.name, **api_observation.model_dump())
    return Response(response.model_dump(mode="json"), status=status)


class LLMHostViewBase(SmarterAuthenticatedAPIView):
    """
    Base class for views of one LLMHost, identified by ``hashed_id`` or ``llmhost_id``.

    :meth:`get_llmhost` returns the LLMHost only if the user may read it, or, with
    ``owner=True``, only if the user owns it. Otherwise it raises :class:`~django.http.Http404`,
    so that the LLMHosts of other accounts are not disclosed.
    """

    service_class = LLMHostService

    def get_llmhost(self, request: Request, owner: bool = False, **kwargs) -> LLMHost:
        """
        Return the LLMHost in the URL, if the user may read it, or own it.

        :param request: The request.
        :param owner: Whether the user must own the LLMHost, rather than only read it.
        :param kwargs: The URL's kwargs: ``hashed_id``, or ``llmhost_id``.
        :returns: The LLMHost.
        :raises Http404: if the URL names no LLMHost, or one that the user may not read, or own.
        """
        hashed_id = kwargs.get("hashed_id")
        if hashed_id:
            llmhost_id = LLMHost.id_from_hashed_id(hashed_id)
        else:
            llmhost_id = kwargs.get("llmhost_id")
        if not llmhost_id:
            raise Http404("LLMHost not found")
        if owner:
            queryset = LLMHost.objects.with_ownership_permission_for(user=request.user)  # type: ignore[attr-defined]
        else:
            queryset = LLMHost.objects.with_read_permission_for(user=request.user)  # type: ignore[attr-defined]
        queryset = queryset.select_related("user_profile__user", "user_profile__account")
        llmhost = queryset.filter(pk=llmhost_id).first()
        if llmhost is None:
            raise Http404("LLMHost not found")
        return llmhost

    def get_service(self) -> LLMHostService:
        """A new instance of :attr:`service_class`, which tests may replace."""
        return self.service_class()


class LLMHostView(LLMHostViewBase):
    """Read, or destroy and delete, an LLMHost."""

    serializer_class = LLMHostSerializer

    def get(self, request: Request, *args, **kwargs):
        """Return an LLMHost that the user may read."""
        llmhost = self.get_llmhost(request, **kwargs)
        return Response(LLMHostApiLLMHost.from_model(llmhost, request.user).model_dump(mode="json"))

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
        """
        Observe an LLMHost that the user may read, in the cluster, now.

        The observation is saved only when the user owns the LLMHost.

        :param request: The request.
        :returns: The LLMHost's status.
        """
        llmhost = self.get_llmhost(request, **kwargs)
        is_owner = llmhost.user_profile.user == request.user
        observation = self.get_service().observe(llmhost, persist=is_owner)
        return host_status(llmhost, observation)


class LLMHostLogsView(LLMHostViewBase):
    """The recent logs of an LLMHost that the user owns."""

    def get(self, request: Request, *args, **kwargs):
        """
        Return the inference server's last ``?tail=`` log lines, 200 by default.

        :param request: The request.
        :returns: The logs, or 400 if ``tail`` is not an integer.
        """
        llmhost = self.get_llmhost(request, owner=True, **kwargs)
        try:
            tail = int(request.query_params.get("tail", 200))
        except ValueError:
            return error("tail must be an integer.")
        try:
            logs = self.get_service().logs(llmhost, tail=tail)
        except LLMHostServiceError as e:
            return service_error(e)
        return Response(LLMHostApiLogs(llmhost=llmhost.name, logs=logs).model_dump(mode="json"))


class LLMHostPlanView(LLMHostViewBase):
    """The Kubernetes resources that deploy would apply, with secrets redacted."""

    def get(self, request: Request, *args, **kwargs):
        """
        Return the Kubernetes resources that deploying an LLMHost that the user owns would apply.

        :param request: The request.
        :returns: The resources, with secrets redacted.
        """
        llmhost = self.get_llmhost(request, owner=True, **kwargs)
        try:
            resources = self.get_service().plan(llmhost)
        except LLMHostServiceError as e:
            return service_error(e)
        return Response(LLMHostApiPlan(llmhost=llmhost.name, resources=resources).model_dump(mode="json"))


class LLMHostDeployView(LLMHostViewBase):
    """Launch an LLMHost that the user owns."""

    def post(self, request: Request, *args, **kwargs):
        """
        Launch an LLMHost that the user owns: apply its Kubernetes resources, and invalidate the cache.

        :param request: The request.
        :returns: 202 with the LLMHost's status.
        """
        llmhost = self.get_llmhost(request, owner=True, **kwargs)
        try:
            observation = self.get_service().launch(llmhost)
        except LLMHostServiceError as e:
            return service_error(e)
        invalidate_all_cached_llmhosts_for_user_profile(llmhost.user_profile)
        return host_status(llmhost, observation, HTTPStatus.ACCEPTED)


class LLMHostUndeployView(LLMHostViewBase):
    """Destroy the Kubernetes resources of an LLMHost that the user owns.

    ``?purge=true`` also deletes its model volume.
    """

    def post(self, request: Request, *args, **kwargs):
        """
        Destroy the Kubernetes resources of an LLMHost that the user owns, and invalidate the cache.

        :param request: The request. ``?purge=true`` also deletes the model volume.
        :returns: The LLMHost's status after it was undeployed.
        """
        llmhost = self.get_llmhost(request, owner=True, **kwargs)
        purge = str(request.query_params.get("purge", "false")).lower() == "true"
        try:
            self.get_service().destroy(llmhost, purge=purge)
        except LLMHostServiceError as e:
            return service_error(e)
        invalidate_all_cached_llmhosts_for_user_profile(llmhost.user_profile)
        response = LLMHostApiUndeployed(
            llmhost=llmhost.name, status=llmhost.status, message=llmhost.status_message  # type: ignore[arg-type]
        )
        return Response(response.model_dump(mode="json"))


class LLMHostReportView(SmarterAuthenticatedAPIView):
    """A summary of the LLMHosts that the user owns: status, GPUs and cost."""

    def get(self, request: Request, *args, **kwargs):
        """
        Return a summary of the LLMHosts that the user owns.

        :param request: The request.
        :returns: The report.
        """
        llmhosts = LLMHost.objects.with_ownership_permission_for(user=request.user)  # type: ignore[attr-defined]
        llmhosts = llmhosts.select_related("user_profile__user").order_by("name")
        report = LLMHostService().report(llmhosts)
        return Response(report)


class LLMHostDiscoverView(SmarterAuthenticatedAPIView):
    """Search a model catalog: ``?q=``, ``?task=text-generation|embedding``, ``?catalog=huggingface|builtin``, ``?limit=``."""

    def get(self, request: Request, *args, **kwargs):
        """
        Search a model catalog.

        Calls the catalog, e.g. the Hugging Face Hub.

        :param request: The request.
        :returns: The matching models, at most :data:`MAX_DISCOVERY_RESULTS`, or 400 if ``limit``
            is not an integer, or 503 if the catalog is unavailable.
        """
        params = request.query_params
        try:
            requested_limit = int(params.get("limit", 20))
        except ValueError:
            return error("limit must be an integer.")
        limit = min(requested_limit, MAX_DISCOVERY_RESULTS)
        limit = max(1, limit)
        try:
            models = LLMHostService().search_models(
                query=params.get("q"),
                task=params.get("task"),
                catalog=params.get("catalog", "huggingface"),
                limit=limit,
            )
        except LLMHostServiceError as e:
            return service_error(e)
        catalog_models = [LLMHostApiCatalogModel.from_model_info(model) for model in models]
        response = LLMHostApiDiscovery(models=catalog_models)
        return Response(response.model_dump(mode="json"))


class LLMHostDiscoverManifestView(SmarterAuthenticatedAPIView):
    """Draft a manifest: ``?repository=`` (required), ``?catalog=``, ``?engine=``, ``?name=``, ``?tokenSecret=``."""

    def get(self, request: Request, *args, **kwargs):
        """
        Draft an LLMHost manifest for a model in a catalog.

        :param request: The request.
        :returns: The manifest, or 400 if ``repository`` is missing, or 503 if the catalog is
            unavailable.
        """
        params = request.query_params
        repository = params.get("repository")
        if not repository:
            return error("repository is required.")
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
        return Response(LLMHostApiDraftManifest(manifest=manifest).model_dump(mode="json"))


class LLMHostListView(ContractListMixin, SmarterAuthenticatedListAPIView):
    """The LLMHosts that the user may read."""

    serializer_class = LLMHostSerializer
    contract_model = LLMHostApiLLMHost

    def item(self, row):
        """An LLMHost of the response, whose ``canDelete`` is the requesting user's."""
        return LLMHostApiLLMHost.from_model(row, self.request.user).model_dump(mode="json")

    def get_queryset(self, *args, **kwargs) -> QuerySet[LLMHost]:
        """The LLMHosts that the user may read, by name."""
        return LLMHost.objects.with_read_permission_for(user=self.request.user).order_by("name")  # type: ignore[attr-defined]
