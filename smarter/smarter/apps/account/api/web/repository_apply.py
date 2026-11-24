"""
The Apply page's batch apply of a GitHub repository, under the console's account api, ``/api/web/account/repository-apply/``.

- ``GET repository-apply/``: the user's recent runs, the newest first, without their manifests.
- ``POST repository-apply/``, ``{"url": "https://github.com/<owner>/<repo>"}``: start a run, or return the one
  in progress. See :func:`smarter.apps.account.repository_apply.start_repository_apply`.
- ``GET repository-apply/<id>/``: a run's progress, with each manifest's state, which the page polls.

Every response is camelCase JSON, from the Pydantic models of :mod:`smarter.apps.account.repository_apply`.
"""

from http import HTTPStatus

from django import http

from smarter.apps.account.models import RepositoryApply, UserProfile, get_resolved_user
from smarter.apps.account.repository_apply import (
    RepositoryApplyRefused,
    RepositoryApplyResponse,
    recent_runs,
    start_repository_apply,
)
from smarter.lib import json, logging
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


def request_user_profile(request) -> UserProfile:
    """
    Return the profile that the request's user acts as: the one that they chose in the user menu, or their newest.

    :param request: The request.
    :returns: The profile.
    """
    user = get_resolved_user(request.user)
    user_profile: UserProfile = UserProfile.get_cached_object(user=user)  # type: ignore[assignment,arg-type]
    return user_profile


def requested_url(request) -> str:
    """
    Return the repository url in the request's JSON body, ``{"url": "..."}``, or an empty string.

    :param request: The request.
    :returns: The url.
    """
    try:
        body = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return ""
    if not isinstance(body, dict):
        return ""
    url = body.get("url")
    if not isinstance(url, str):
        return ""
    return url


class RepositoryApplyView(SmarterAuthenticatedNeverCachedWebView):
    """
    List the user's recent batch applies (``GET``), or start one (``POST``).

    ``POST`` responds 202 with the new run's progress, or 200 with the run that is already in progress, or
    400 with ``{"error": ...}`` when the url isn't a public GitHub repository's, or the user may not start one now.
    """

    def get(self, request, *args, **kwargs):
        """
        Return the user's recent runs.

        :param request: The request.
        :returns: A json response, see :class:`~smarter.apps.account.repository_apply.RepositoryApplyListResponse`.
        """
        runs = recent_runs(request_user_profile(request))
        return http.JsonResponse(status=HTTPStatus.OK.value, data=runs.model_dump(mode="json"))

    def post(self, request, *args, **kwargs):
        """
        Start a batch apply of the repository in the body, unless one of the user's is in progress.

        :param request: The request.
        :returns: A json response with the run's progress, see
            :class:`~smarter.apps.account.repository_apply.RepositoryApplyResponse`.
        """
        user_profile = request_user_profile(request)
        try:
            run, started = start_repository_apply(user_profile, requested_url(request))
        except RepositoryApplyRefused as e:
            logger.info("refused a batch apply for user profile %s: %s", user_profile.pk, e)
            return http.JsonResponse(status=HTTPStatus.BAD_REQUEST.value, data={"error": str(e)})
        status = HTTPStatus.ACCEPTED if started else HTTPStatus.OK
        progress = RepositoryApplyResponse.from_model(run)
        return http.JsonResponse(status=status.value, data=progress.model_dump(mode="json"))


class RepositoryApplyDetailView(SmarterAuthenticatedNeverCachedWebView):
    """Return the progress of one of the user's batch applies, with each manifest's state, which the page polls."""

    def get(self, request, *args, run_id: int = 0, **kwargs):
        """
        Return a run's progress.

        :param request: The request.
        :param run_id: The run's id.
        :returns: A json response with its progress, or 404 if the user has no such run.
        """
        user_profile = request_user_profile(request)
        run = RepositoryApply.objects.filter(pk=run_id, user_profile__user=user_profile.user).first()
        if run is None:
            return http.JsonResponse(status=HTTPStatus.NOT_FOUND.value, data={"error": "Not found."})
        progress = RepositoryApplyResponse.from_model(run)
        return http.JsonResponse(status=HTTPStatus.OK.value, data=progress.model_dump(mode="json"))
