# pylint: disable=W0613
"""
API view for the web console's onboarding hints, which the React package ``@smarter/onboarding`` shows.

An onboarding hint points a new user to where to go next: a spotlight on the sidebar's LLM Clients
link, then on the Get Weather LLMClient, then a guided tour of the Prompt Engineer's Workbench. Each
shows by itself until the user has done something with it, which ``onboarding/seen/`` records, as an
:class:`~smarter.apps.dashboard.models.OnboardingHint`. Each page learns which hints the user has
seen from :func:`onboarding_context`, which ``templates/react/onboarding.html`` writes into the page,
so that a hint needs no request before it shows.
"""

from http import HTTPStatus

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
from smarter.lib.cache import cache_results
from smarter.lib.django.views import SmarterAuthenticatedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)


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


class OnboardingContext(BaseModel):
    """
    The onboarding state that ``templates/react/onboarding.html`` writes into each console page, as JSON.

    :param enabled: Whether hints show by themselves: the ``enable_web_console_onboarding_hints`` waffle
        switch.
    :param api_url: The onboarding seen api.
    :param seen: The hints that the user has seen.
    :param csrf_cookie_name: The name of the CSRF cookie, which the api requires.
    :param cookie_domain: The domain of the session cookies.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    enabled: bool
    api_url: str = Field(alias="apiUrl")
    seen: list[OnboardingHints]
    csrf_cookie_name: str = Field(alias="csrfCookieName")
    cookie_domain: str = Field(alias="cookieDomain")


@cache_results()
def seen_onboarding_hints(user_id: int) -> list[str]:
    """
    The onboarding hints that the user has seen, in the order of :class:`OnboardingHints`.

    Every console page asks, so the answer is cached until :class:`OnboardingSeenView` invalidates it.

    :param user_id: The id of the Django user.
    :type user_id: int
    :returns: The ids of the hints that the user has seen.
    :rtype: list[str]
    """
    seen = set(OnboardingHint.objects.filter(user_id=user_id).values_list("hint", flat=True))
    return [hint.value for hint in OnboardingHints if hint.value in seen]


def onboarding_context(user: User | None, api_url: str) -> OnboardingContext:
    """
    The onboarding state of a console page.

    :param user: The signed-in user, or None, for whom no hint shows.
    :type user: django.contrib.auth.models.User | None
    :param api_url: The onboarding seen api.
    :type api_url: str
    :returns: The state that the page's React apps read.
    :rtype: OnboardingContext
    """
    signed_in = isinstance(user, User)
    return OnboardingContext(
        enabled=signed_in and switch_is_active(SmarterWaffleSwitches.ENABLE_WEB_CONSOLE_ONBOARDING_HINTS),
        api_url=api_url,
        seen=[OnboardingHints(hint) for hint in seen_onboarding_hints(user.pk)] if signed_in else [],
        csrf_cookie_name=settings.CSRF_COOKIE_NAME,
        cookie_domain=settings.SESSION_COOKIE_DOMAIN or "",
    )


class OnboardingSeenView(SmarterAuthenticatedWebView):
    """
    Records what the user did with an onboarding hint, which then no longer shows by itself.

    The body is an :class:`OnboardingSeenRequest`, as JSON. The first outcome is kept: a hint that the
    user has already seen is left as it is. The response is an :class:`OnboardingApiResponse`:

    .. code-block:: json

        {"seen": ["sidebar_llmclients", "llmclient_weather"]}
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
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
