"""
The REST api's token usage, ``GET /api/v1/accounts/usage/``: the tokens that the user's LLM requests used.

The series is the one that the web console's dashboard charts, built by
:mod:`smarter.apps.account.token_usage`.
"""

from http import HTTPStatus

from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.account.models import UserProfile, get_resolved_user
from smarter.apps.account.token_usage import TokenUsageWindow, token_usage_series
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


class TokenUsageView(SmarterAuthenticatedAPIView):
    """
    The tokens that the user's LLM requests used, over a window of time.

    ``?periodicity=24_hours`` names the window, one of :attr:`TokenUsageWindow.WINDOWS`. The response is a
    :class:`~smarter.apps.account.token_usage.TokenUsageSeries` of the charges to the user's UserProfile,
    cached for five minutes. An unknown periodicity is a 400.
    """

    def get(self, request: Request, *args, **kwargs) -> Response:
        """
        Return the user's token usage over the window of the query's ``periodicity``.

        :param request: The request.
        :returns: The window's points, or 400 if the periodicity is unknown.
        """
        periodicity = request.query_params.get("periodicity") or TokenUsageWindow.DEFAULT
        try:
            TokenUsageWindow.get(periodicity)
        except ValueError as e:
            return Response({"detail": str(e)}, status=HTTPStatus.BAD_REQUEST)
        user = get_resolved_user(request.user)
        user_profile = UserProfile.get_cached_object(user=user)  # type: ignore[arg-type]
        logger.debug("%s.get() periodicity=%s", self.formatted_class_name, periodicity)
        series = token_usage_series(user_profile.record_locator, periodicity)  # type: ignore[union-attr]
        return Response(series, status=HTTPStatus.OK)


__all__ = ["TokenUsageView"]
