# pylint: disable=W0718,W0613
"""Orchestrator api/v1/orchestrator CRUD views."""

from http import HTTPStatus
from typing import Optional

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import (
    HttpRequest,
    HttpResponseNotFound,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from pydantic import ValidationError as PydanticValidationError
from rest_framework.exceptions import (
    APIException,
    NotFound,
    ParseError,
    PermissionDenied,
)
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.account.models import User, UserProfile, get_resolved_user
from smarter.apps.orchestrator.contract.models import (
    OrchestratorApiOrchestrator,
    OrchestratorApiRun,
    OrchestratorApiRunRequest,
)
from smarter.apps.orchestrator.models import (
    OrchestrationRun,
    Orchestrator,
)
from smarter.apps.orchestrator.runtime import OrchestrationRefused, start_run
from smarter.apps.orchestrator.serializers import (
    OrchestratorSerializer,
)
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.contract import ContractListMixin
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAdminAPIView,
    SmarterAdminListAPIView,
    SmarterAuthenticatedAPIView,
)
from smarter.lib.typing import SmarterDictType, required

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
        """
        The queryset of the one Orchestrator that the request names.

        :returns: A queryset holding :attr:`orchestrator`.
        """
        orchestrator = required(self.orchestrator, "orchestrator")
        return Orchestrator.objects.filter(id=orchestrator.id)

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        """
        Remove ``hashed_id`` from the url kwargs, for :meth:`initial`, then dispatch the request.

        :param request: The request.
        :returns: The response.
        """
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
        """
        Return the Orchestrator, serialized as a :class:`OrchestratorApiOrchestrator`.

        :param request: The request.
        :param orchestrator_id: The Orchestrator's id, from the url; :meth:`initial` has already found it.
        :returns: The Orchestrator, with ``200``.
        :raises NotFound: when the request names no Orchestrator.
        """
        if self.orchestrator:
            return Response(
                OrchestratorApiOrchestrator.from_model(self.orchestrator, request.user).model_dump(mode="json"),
                status=HTTPStatus.OK,
            )
        raise NotFound("Orchestrator not found")

    def post(self, request: Request, *args, **kwargs):
        """
        Create an Orchestrator from the request body's fields, then redirect to it.

        :param request: The request, whose JSON body holds the Orchestrator's fields.
        :returns: A redirect to the new Orchestrator's url, or ``400`` if it could not be created.
        """
        try:
            data = request.data
            if not isinstance(data, dict):
                raise TypeError(f"Expected a JSON dict in request body but received {type(data)}")
            orchestrator = Orchestrator.objects.create(**data)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(orchestrator.id) + "/")  # type: ignore[return-value]

    def patch(self, request: Request, *args, orchestrator_id: Optional[int] = None, **kwargs):
        """
        Set the Orchestrator's attributes from the request body, save it, then redirect to it.

        Keys that are not attributes of the Orchestrator are ignored.

        :param request: The request, whose JSON body is a dict of attribute values.
        :param orchestrator_id: The Orchestrator's id, from the url; :meth:`initial` has already found it.
        :returns: A redirect to the request's url; ``404`` if there is no Orchestrator; ``400`` if the body is
            not a dict or the Orchestrator does not validate; ``500`` if saving fails.
        """
        orchestrator: Optional[Orchestrator] = None
        data: Optional[SmarterDictType] = None

        orchestrator = self.orchestrator
        if not orchestrator:
            return HttpResponseNotFound("Orchestrator not found")

        try:
            request_data = request.data
            if not isinstance(request_data, dict):
                return JsonResponse(
                    {
                        "error": f"Invalid request data. Expected a JSON dict in request body but received {type(request_data)}"
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
            data = request_data
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
        """
        Delete the Orchestrator, then redirect to the parent url.

        A superuser may delete any Orchestrator by its id; other users delete the Orchestrator that :meth:`initial` found.

        :param request: The request.
        :param orchestrator_id: The Orchestrator's id, from the url.
        :returns: A redirect to the url two levels up, or ``500`` if deleting fails.
        """
        orchestrator: Optional[Orchestrator]
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

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        """
        Dispatch the request, then set :attr:`orchestrators` to the Orchestrators the user may read, unless it failed.

        :param request: The request.
        :returns: The response.
        """
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code > 299:
            return response
        self.orchestrators = Orchestrator.objects.with_read_permission_for(user=request.user)  # type: ignore[assignment]
        return response

    def get_queryset(self, *args, **kwargs):
        """
        The Orchestrators that the user may read, ordered by name.

        :returns: The queryset, with its owners and tags fetched.
        """
        return (
            Orchestrator.objects.with_read_permission_for(user=self.user)  # type: ignore[return-value]
            .select_related("user_profile__user", "user_profile__account")
            .prefetch_related("tags")
            .order_by("name")
        )


###############################################################################
# Run views (ADR-037)
###############################################################################
class OrchestrationRunRefused(APIException):
    """A run that may not start, e.g. of a strategy that can't run yet: a 400 with its reason."""

    status_code = HTTPStatus.BAD_REQUEST
    default_code = "run_refused"


def readable_orchestrator(user: User, hashed_id: Optional[str], orchestrator_id: Optional[int]) -> Orchestrator:
    """
    Return the Orchestrator that a run url names, if the user may read it.

    :param user: The request's user.
    :param hashed_id: The Orchestrator's hashed id, from the url, if it names it so.
    :param orchestrator_id: Its id, from the url, otherwise.
    :returns: The Orchestrator.
    :raises NotFound: If there is none, or the user may not read it.
    """
    if hashed_id:
        orchestrator_id = Orchestrator.id_from_hashed_id(hashed_id)
    orchestrators = Orchestrator.objects.with_read_permission_for(user=user)  # type: ignore[attr-defined]
    orchestrator = orchestrators.filter(pk=orchestrator_id).first()
    if orchestrator is None:
        raise NotFound("Orchestrator not found")
    return orchestrator


def request_user(request: Request) -> User:
    """
    Return the request's user, whom DRF has authenticated.

    :param request: The request.
    :returns: The user.
    :raises NotFound: If the request has no user, which authentication doesn't let through.
    """
    user = get_resolved_user(request.user)
    if not isinstance(user, User):
        raise NotFound("Orchestrator not found")
    return user


def runner_profile(user: User, orchestrator: Orchestrator, current: Optional[UserProfile]) -> UserProfile:
    """
    Return the profile that a run records as its starter: the user's in the Orchestrator's account, if they have one.

    :param user: The request's user.
    :param orchestrator: The Orchestrator.
    :param current: The request's user profile, for a user who reads the Orchestrator from another account.
    :returns: The profile.
    :raises NotFound: If the user has no profile at all.
    """
    in_account = UserProfile.objects.filter(user=user, account_id=orchestrator.user_profile.account_id).first()  # type: ignore[union-attr]
    if in_account is not None:
        return in_account
    if current is None:
        raise NotFound("Orchestrator not found")
    return current


class OrchestrationRunsView(SmarterAuthenticatedAPIView):
    """
    Start a run of an Orchestrator: ``POST /api/v1/orchestrators/<hashed_id>/runs/`` with an objective.

    It answers ``202`` with the run, ``pending``, which a Celery task executes. See
    :mod:`smarter.apps.orchestrator.runtime`.
    """

    def post(self, request: Request, hashed_id: Optional[str] = None, orchestrator_id: Optional[int] = None):
        """
        Start a run.

        :param request: The request, whose body is an :class:`OrchestratorApiRunRequest`.
        :param hashed_id: The Orchestrator's hashed id, from the url.
        :param orchestrator_id: Its id, from the url.
        :returns: The run, an :class:`OrchestratorApiRun`, with ``202``.
        :raises NotFound: If the user may not read the Orchestrator.
        :raises ParseError: If the body isn't an objective.
        :raises PermissionDenied: If the user may not use every LLMClient of the Orchestrator.
        :raises OrchestrationRunRefused: If the run may not start, e.g. its strategy can't run yet.
        """
        user = request_user(request)
        orchestrator = readable_orchestrator(user, hashed_id, orchestrator_id)
        try:
            body = OrchestratorApiRunRequest.model_validate(request.data)
        except PydanticValidationError as e:
            raise ParseError("The body must be a JSON object with an objective.") from e
        user_profile = runner_profile(user, orchestrator, self.user_profile)  # type: ignore[arg-type]
        try:
            run = start_run(orchestrator, user_profile, body.objective)
        except OrchestrationRefused as e:
            if e.status == HTTPStatus.FORBIDDEN:
                raise PermissionDenied(str(e)) from e
            raise OrchestrationRunRefused(str(e)) from e
        data = OrchestratorApiRun.from_model(run).model_dump(mode="json")
        return Response(data, status=HTTPStatus.ACCEPTED)


class OrchestrationRunView(SmarterAuthenticatedAPIView):
    """
    A run of an Orchestrator: ``GET /api/v1/orchestrators/<hashed_id>/runs/<run_id>/``.

    Only the user who started it, or a superuser, may read it: its result may hold what that user may read in other
    accounts.
    """

    def get(
        self, request: Request, run_id: int, hashed_id: Optional[str] = None, orchestrator_id: Optional[int] = None
    ):
        """
        Return the run, with its steps.

        :param request: The request.
        :param run_id: The run's id, from the url.
        :param hashed_id: The Orchestrator's hashed id, from the url.
        :param orchestrator_id: Its id, from the url.
        :returns: The run, an :class:`OrchestratorApiRun`.
        :raises NotFound: If there is no such run of the Orchestrator, or the user didn't start it.
        """
        user = request_user(request)
        orchestrator = readable_orchestrator(user, hashed_id, orchestrator_id)
        runs = OrchestrationRun.objects.select_related("started_by__user", "started_by__account")
        run = runs.filter(pk=run_id, orchestrator=orchestrator).first()
        if run is None:
            raise NotFound("Run not found")
        started_by_user_id = run.started_by.user_id if run.started_by else None  # type: ignore[attr-defined]
        if not user.is_superuser and started_by_user_id != user.pk:
            raise NotFound("Run not found")
        data = OrchestratorApiRun.from_model(run).model_dump(mode="json")
        return Response(data)
