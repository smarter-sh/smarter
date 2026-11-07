# pylint: disable=W0613
"""
API view for the web console's onboarding hints, which the React package ``@smarter/onboarding`` shows.

An onboarding hint points a new user to where to go next: a spotlight on the sidebar's LLM Clients
link, then on the Get Weather LLMClient, then a guided tour of the Prompt Engineer's Workbench. Each
shows by itself until the user has done something with it, which ``onboarding/seen/`` records, as an
:class:`~smarter.apps.dashboard.models.OnboardingHint`. Each page learns which hints the user has
seen from the console's session (``GET /api/web/session/``), which lists them, so that a hint needs no
request before it shows.
"""

from http import HTTPStatus

from cache_results import cache_results
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from smarter.apps.account.models import User, get_resolved_user
from smarter.apps.dashboard.models import (
    OnboardingHint,
    OnboardingHints,
    OnboardingOutcomes,
)
from smarter.lib import json, logging
from smarter.lib.django.views import SmarterAuthenticatedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)


class OnboardingSeenRequest(BaseModel):
    """
    The body of a request to the onboarding seen api.

    :param hint: The hint, one of :class:`~smarter.apps.dashboard.models.OnboardingHints`.
    :param outcome: What the user did with it, one of
        :class:`~smarter.apps.dashboard.models.OnboardingOutcomes`.
    """

    model_config = ConfigDict(extra="forbid")

    hint: OnboardingHints
    outcome: OnboardingOutcomes


class OnboardingApiResponse(BaseModel):
    """
    The response of the onboarding seen api.

    :param seen: The hints that the user has seen, which no longer show by themselves.
    """

    model_config = ConfigDict(extra="forbid")

    seen: list[OnboardingHints]


@cache_results()
def seen_onboarding_hints(user_id: int) -> list[str]:
    """
    The onboarding hints that the user has seen, in the order of :class:`OnboardingHints`.

    The console's session asks on every load, so the answer is cached until :class:`OnboardingSeenView` invalidates it.

    :param user_id: The id of the Django user.
    :type user_id: int
    :returns: The ids of the hints that the user has seen.
    :rtype: list[str]
    """
    seen = set(OnboardingHint.objects.filter(user_id=user_id).values_list("hint", flat=True))
    return [hint.value for hint in OnboardingHints if hint.value in seen]


class OnboardingSeenView(SmarterAuthenticatedWebView):
    """
    Records what the user did with an onboarding hint, which then no longer shows by itself.

    The body is an :class:`OnboardingSeenRequest`, as JSON. The first outcome is kept: a hint that the
    user has already seen is left as it is. The response is an :class:`OnboardingApiResponse`:

    .. code-block:: json

        {"seen": ["sidebar_llmclients", "llmclient_weather"]}
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Record the outcome of an onboarding hint, unless the user has one, and invalidate their cached hints.

        :param request: The request.
        :returns: The hints the user has seen, as JSON; ``401`` if not signed in; ``400`` if the body
            is invalid.
        """
        user = get_resolved_user(request.user)
        if not isinstance(user, User):
            return JsonResponse({"error": "Not signed in."}, status=HTTPStatus.UNAUTHORIZED)
        try:
            body = OnboardingSeenRequest.model_validate(json.loads(request.body or b"{}"))
        except (ValueError, ValidationError) as e:
            logger.warning("%s.OnboardingSeenView.post() invalid body for user %s: %s", logger_prefix, user.pk, e)
            return JsonResponse({"error": "Invalid request body."}, status=HTTPStatus.BAD_REQUEST)
        _, created = OnboardingHint.objects.get_or_create(
            user=user, hint=body.hint.value, defaults={"outcome": body.outcome.value}
        )
        seen_onboarding_hints.invalidate(user.pk)
        logger.info(
            "%s.OnboardingSeenView.post() user %s, hint %s, outcome %s, new: %s",
            logger_prefix,
            user.pk,
            body.hint.value,
            body.outcome.value,
            created,
        )
        response = OnboardingApiResponse(seen=[OnboardingHints(hint) for hint in seen_onboarding_hints(user.pk)])
        return JsonResponse(response.model_dump(mode="json"), status=HTTPStatus.OK)
