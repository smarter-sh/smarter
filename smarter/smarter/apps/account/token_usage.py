"""
Token usage: the tokens that a user's LLM requests used, over a recent window of time, one point per hour, day or month.

Each LLM request creates a :class:`~smarter.apps.account.models.Charge` for each resource that it
is charged to, the user's :class:`~smarter.apps.account.models.UserProfile` among them. Celery Beat
rolls charges up into :class:`~smarter.apps.account.models.AggregatedCharges` every hour, and
deletes them, so each point is summed from both, by
:func:`~smarter.apps.account.models.get_actuals`, as the budgets are. The charges of the current
hour are therefore counted before they're aggregated.

- :class:`TokenUsageWindow`: the windows of time, e.g. the last 24 hours, by hour.
- :func:`token_usage_series`: the points of a window, cached for five minutes.

The web console's dashboard charts them (:class:`smarter.apps.dashboard.views.views.api.charges.ChargesView`),
and the REST api returns them at ``GET /api/v1/accounts/usage/``
(:class:`smarter.apps.account.api.v1.views.usage.TokenUsageView`).
"""

from datetime import datetime
from typing import Literal, Optional

from cache_results import cache_results
from django.utils import timezone
from pydantic import BaseModel, ConfigDict, Field

from smarter.apps.account.models import get_actuals
from smarter.apps.account.models.budget import BudgetPeriod, add_periods, period_start

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

    period_start: datetime = Field(..., description="The start of the period, in UTC.")
    records: int = Field(..., description="How many charges the period has.")
    prompt_tokens: int = Field(..., description="The tokens of the prompts.")
    completion_tokens: int = Field(..., description="The tokens of the completions.")
    total_tokens: int = Field(..., description="Every token of the period.")
    total_cost: float = Field(..., description="The period's cost, in US dollars.")


class TokenUsageSeries(BaseModel):
    """The Token Usage chart's points for one window, oldest first."""

    model_config = ConfigDict(extra="forbid")

    periodicity: str = Field(..., description="The window, e.g. 24_hours. See TokenUsageWindow.")
    period: TokenUsagePeriod = Field(..., description="The period of each point.")
    points: list[TokenUsagePoint] = Field(..., description="One point per period, oldest first.")


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


TOKEN_USAGE_API_MODELS = (TokenUsageSeries,)
"""The models whose JSON Schemas the Smarter api's OpenAPI document includes."""

__all__ = [
    "TOKEN_USAGE_API_MODELS",
    "TOKEN_USAGE_CACHE_TIMEOUT",
    "TokenUsagePeriod",
    "TokenUsagePoint",
    "TokenUsageSeries",
    "TokenUsageWindow",
    "build_token_usage_series",
    "token_usage_series",
]
