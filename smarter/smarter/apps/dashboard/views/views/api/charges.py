# pylint: disable=W0613
"""
Smarter.apps.dashboard.views.api.charges
=========================================

API view for the dashboard's Token Usage chart: the tokens that a user's LLM requests used, over
a recent window of time, one point per hour, day or month. The series is built by
:mod:`smarter.apps.account.token_usage`, which the REST api's ``GET /api/v1/accounts/usage/`` shares.

- :class:`ChargesView`: the authenticated POST endpoint, ``{"periodicity": "24_hours"}``.
"""

from http import HTTPStatus

from django.http import HttpRequest, JsonResponse

from smarter.apps.account.models import UserProfile, get_resolved_user
from smarter.apps.account.token_usage import TokenUsageWindow, token_usage_series
from smarter.lib import json, logging
from smarter.lib.django.views import SmarterAuthenticatedWebView

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)


def requested_periodicity(request: HttpRequest) -> str:
    """
    The periodicity in the request's JSON body, ``{"periodicity": "24_hours"}``, or the default.

    :param request: The incoming HTTP POST request.
    :type request: django.http.HttpRequest
    :returns: The requested periodicity, or :attr:`TokenUsageWindow.DEFAULT` if the body has none.
    :rtype: str
    """
    try:
        body = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return TokenUsageWindow.DEFAULT
    periodicity = body.get("periodicity") if isinstance(body, dict) else None
    return periodicity if isinstance(periodicity, str) else TokenUsageWindow.DEFAULT


class ChargesView(SmarterAuthenticatedWebView):
    """
    API view for the dashboard's Token Usage chart: the user's token usage over a window of time.

    A ``POST`` with ``{"periodicity": "<window>"}`` returns a :class:`TokenUsageSeries` of the
    charges to the user's UserProfile. An unknown periodicity is a 400.
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns the class name in a formatted string along with the name of this view."""
        class_name = f"{__name__}.{ChargesView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to return the user's token usage over a window of time.

        :param request: The incoming HTTP POST request, whose JSON body may name a periodicity.
        :type request: django.http.HttpRequest
        :returns: The window's points, or a 400 with the error if the periodicity is unknown.
        :rtype: django.http.JsonResponse
        """
        user = get_resolved_user(request.user)
        user_profile = UserProfile.get_cached_object(user=user)  # type: ignore
        periodicity = requested_periodicity(request)
        logger.debug("%s.post() periodicity=%s", self.formatted_class_name, periodicity)
        try:
            TokenUsageWindow.get(periodicity)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return JsonResponse(token_usage_series(user_profile.record_locator, periodicity), status=HTTPStatus.OK)
