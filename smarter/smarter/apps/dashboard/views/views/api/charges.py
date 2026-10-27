# pylint: disable=W0613
"""
Smarter.apps.dashboard.views.api.charges
=========================================

API view for the dashboard's Token Usage chart: the tokens that a user's LLM requests used, over
a recent window of time, one point per hour, day or month.

Each LLM request creates a :class:`~smarter.apps.account.models.Charge` for each resource that it
is charged to, the user's :class:`~smarter.apps.account.models.UserProfile` among them. Celery Beat
rolls charges up into :class:`~smarter.apps.account.models.AggregatedCharges` every hour, and
deletes them, so each point is summed from both, by
:func:`~smarter.apps.account.models.get_actuals`, as the budgets are. The charges of the current
hour are therefore counted before they're aggregated.

- :class:`TokenUsageWindow`: the windows that the chart offers, e.g. the last 24 hours, by hour.
- :func:`token_usage_series`: the points of a window, cached for five minutes.
- :class:`ChargesView`: the authenticated POST endpoint, ``{"periodicity": "24_hours"}``.
"""

from datetime import datetime
from http import HTTPStatus
from typing import Literal, Optional

from cache_results import cache_results
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from pydantic import BaseModel, ConfigDict

from smarter.apps.account.models import UserProfile, get_actuals, get_resolved_user
from smarter.apps.account.models.budget import BudgetPeriod, add_periods, period_start
from smarter.lib import json, logging
from smarter.lib.django.views import SmarterAuthenticatedWebView

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)

TOKEN_USAGE_CACHE_TIMEOUT = 5 * 60  # seconds. the chart's newest point may be five minutes behind.

TokenUsagePeriod = Literal["hour", "day", "month"]


class TokenUsageWindow:
    """
    The windows of time that the Token Usage chart offers, by their periodicity key.

    Each is a number of points of one period, ending with the current one: e.g. ``24_hours`` is
    the current hour and the 23 before it. Charges are aggregated by the hour, so an hour is the
    smallest period.
    """

    HALF_DAY = "12_hours"
    DAY = "24_hours"
    WEEK = "7_days"
    MONTH = "1_month"
    YEAR = "1_year"

    DEFAULT = DAY

    WINDOWS: dict[str, tuple[TokenUsagePeriod, int]] = {
        HALF_DAY: ("hour", 12),
        DAY: ("hour", 24),
        WEEK: ("day", 7),
        MONTH: ("day", 30),
        YEAR: ("month", 12),
    }

    @classmethod
    def get(cls, periodicity: str) -> tuple[TokenUsagePeriod, int]:
        """
        Return the period of a window's points, and how many there are.

        :param periodicity: The window's key, e.g. ``"24_hours"``.
        :type periodicity: str
        :returns: The period, ``"hour"``, ``"day"`` or ``"month"``, and the number of points.
        :rtype: tuple[str, int]
        :raises ValueError: If the periodicity is not one of the windows.
        """
        try:
            return cls.WINDOWS[periodicity]
        except KeyError as e:
            raise ValueError(f"Unknown periodicity: {periodicity}. Use one of {', '.join(cls.WINDOWS)}.") from e


class TokenUsagePoint(BaseModel):
    """The tokens and cost of one period of the Token Usage chart."""

    model_config = ConfigDict(extra="forbid")

    period_start: datetime
    records: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    total_cost: float


class TokenUsageSeries(BaseModel):
    """The Token Usage chart's points for one window, oldest first."""

    model_config = ConfigDict(extra="forbid")

    periodicity: str
    period: TokenUsagePeriod
    points: list[TokenUsagePoint]


def build_token_usage_series(
    resource_locator: str, periodicity: str, now: Optional[datetime] = None
) -> TokenUsageSeries:
    """
    Return the tokens that a resource used in each period of a window, oldest first.

    A period without charges is a point of zeros, so that the chart's time axis has no gaps.

    :param resource_locator: The record locator of the resource whose charges are counted, e.g. a
        UserProfile's.
    :type resource_locator: str
    :param periodicity: The window's key, e.g. ``"24_hours"``. See :class:`TokenUsageWindow`.
    :type periodicity: str
    :param now: The end of the window. Defaults to now.
    :type now: Optional[datetime]
    :returns: The window's points.
    :rtype: TokenUsageSeries
    :raises ValueError: If the periodicity is not one of the windows.
    """
    period, count = TokenUsageWindow.get(periodicity)
    budget_period = BudgetPeriod(period)
    now = now or timezone.now()
    start = add_periods(budget_period, period_start(budget_period, now), 1 - count)
    points: list[TokenUsagePoint] = []
    for _ in range(count):
        end = add_periods(budget_period, start, 1)
        actuals = get_actuals(resource_locator, start, min(end, now))
        points.append(
            TokenUsagePoint(
                period_start=start,
                records=actuals.records,
                prompt_tokens=actuals.prompt_tokens,
                completion_tokens=actuals.completion_tokens,
                total_tokens=actuals.total_tokens,
                total_cost=float(actuals.total_cost),
            )
        )
        start = end
    return TokenUsageSeries(periodicity=periodicity, period=period, points=points)


@cache_results(timeout=TOKEN_USAGE_CACHE_TIMEOUT)
def token_usage_series(resource_locator: str, periodicity: str) -> dict:
    """
    The JSON of :func:`build_token_usage_series` for a window that ends now, cached for five minutes.

    :param resource_locator: The record locator of the resource whose charges are counted.
    :type resource_locator: str
    :param periodicity: The window's key. See :class:`TokenUsageWindow`.
    :type periodicity: str
    :returns: The JSON of a :class:`TokenUsageSeries`.
    :rtype: dict
    :raises ValueError: If the periodicity is not one of the windows. Errors aren't cached.
    """
    return build_token_usage_series(resource_locator, periodicity).model_dump(mode="json")


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
