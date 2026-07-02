# pylint: disable=W0613
"""
Smarter.apps.dashboard.views.api.charges.

========================================
This module implements the API logic for aggregated usage charges in the Smarter dashboard application.

Overview
--------
It provides endpoints and utilities for summarizing per-user or per-resource usage costs, intended for
display within frontend dashboard components. The module's main responsibilities are:

- **Aggregated Charges Querying**: Defines functions to efficiently query and aggregate usage charge metrics
  (e.g., tokens, cost) across various time intervals including hour, day, week, month, and year,
  supporting dynamic data visualization in dashboard charts.
- **Periodicity Logic**: Encapsulates business logic to compute time boundaries and grouping fields for different
  reporting periods, used for accurate and flexible charting.
- **API Endpoint**: Exposes an authenticated Django view class (`MyResourcesView`) which serves data to frontend
  React components via a JSON API, supporting POST requests that specify desired aggregation periodicity.

Caching
-------
Resource-intensive queries (e.g., charge aggregation) leverage a cache layer to minimize repeated expensive
computations and database load. The `@cache_results` decorator is used, with a default timeout of one hour.

Usage
-----
To expose the API endpoint, wire up `MyResourcesView` in your Django application's URL configuration. The endpoint
expects POST requests containing a valid periodicity value and returns aggregated charge statistics as JSON.
Use these endpoints to drive dashboard visualizations of account or organization usage.

Note
----
Function signatures and argument details are documented via Sphinx's ``automodule`` directive. For deeper API
reference, see the generated developer docs or inline function docstrings.
"""

from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Any
from zoneinfo import ZoneInfo

from django.db.models import Q, Sum
from django.http import HttpRequest, JsonResponse

from smarter.__version__ import __version__
from smarter.apps.account.models import (
    AggregatedCharges,
    UserProfile,
    get_resolved_user,
)
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.views import (
    SmarterAuthenticatedWebView,
)

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)
server_tz = datetime.now().astimezone().tzinfo


class AggregatedChargesPeriod:
    """
    API view to provide aggregated usage charge data for the dashboard’s "Aggregated Charges Chart".

    React component.

    This view responds to authenticated POST requests, returning per-user usage summaries
    (e.g., tokens and cost) for a requested aggregation period as part of the dashboard experience.

    Inherits from :class:`SmarterAuthenticatedWebView`, which enforces user authentication.

    Attributes
    ----------
    formatted_class_name : str
        Returns the class name and instance identifier as a formatted string,
        helpful for logging and debugging.

    Methods
    -------
    post(request, periodicity, *args, **kwargs)
        Handle POST requests and return aggregated charge data as JSON for the
        specified periodicity.

    Examples
    --------
    Usage in Django’s URL configuration::

        from smarter.apps.dashboard.views.api.charges import MyResourcesView

        urlpatterns = [
            path("api/charges/<str:periodicity>/", MyResourcesView.as_view(), name="api-charges"),
        ]
    """

    HOUR = "1_hour"
    HALF_DAY = "12_hours"
    DAY = "24_hours"
    WEEK = "7_days"
    MONTH = "1_month"
    YEAR = "1_year"

    @classmethod
    def delta(cls, periodicity: str, tz: ZoneInfo | None = None) -> datetime:
        """
        Compute the UTC datetime cutoff for the beginning of a given aggregation period.

        Determines the lower (older) time boundary to use when aggregating charge data, based on
        a specified periodicity key. The returned datetime represents "now minus the length of
        the interval," in the given timezone.

        Parameters
        ----------
        periodicity : str
            The aggregation period key. Must be one of:
            ``"1_hour"``, ``"12_hours"``, ``"24_hours"``, ``"7_days"``, ``"1_month"``, or ``"1_year"``.
        tz : ZoneInfo or None, optional
            Timezone to use for the calculation (defaults to the system local time zone if None).

        Returns
        -------
        datetime
            The datetime value representing the start of the aggregation window.

        Raises
        ------
        ValueError
            If an unknown periodicity key is provided.

        Examples
        --------
        ::

            # Get start of the last 7 days in UTC
            from zoneinfo import ZoneInfo
            cutoff = AggregatedChargesPeriod.delta("7_days", tz=ZoneInfo("UTC"))
        """
        now = datetime.now(tz)

        match periodicity:
            case cls.HOUR:
                return now - timedelta(hours=1)
            case cls.HALF_DAY:
                return now - timedelta(hours=12)
            case cls.DAY:
                return now - timedelta(days=1)
            case cls.WEEK:
                return now - timedelta(weeks=1)
            case cls.MONTH:
                return now - timedelta(days=30)
            case cls.YEAR:
                return now - timedelta(days=365)
            case _:
                raise ValueError(f"Unknown periodicity: {periodicity}")

    @classmethod
    def grouping_fields(cls, periodicity: str) -> list[str]:
        """
        Retrieve the list of model fields used to group charge data for a given periodicity.

        This method assists in dynamically determining how database records should be grouped
        for aggregation, based on the reporting interval requested. It enables flexible
        aggregation (hourly, daily, monthly, etc.) for charge summaries.

        Parameters
        ----------
        periodicity : str
            Aggregation period key. Must be one of the constants defined in
            :class:`AggregatedChargesPeriod` (e.g., ``"1_hour"``, ``"12_hours"``, ``"24_hours"``, ``"7_days"``, ``"1_month"``, ``"1_year"``).

        Returns
        -------
        list of str
            List of model field names that should be used to group charge records for the
            requested periodicity.

        Raises
        ------
        KeyError
            If the supplied periodicity value is not recognized.

        Examples
        --------
        ::

            fields = AggregatedChargesPeriod.grouping_fields("1_month")
            # May return: ['year', 'month', 'day']
        """
        retval = {
            AggregatedChargesPeriod.HOUR: [
                "year",
                "month",
                "day",
                "hour",
            ],
            AggregatedChargesPeriod.HALF_DAY: [
                "year",
                "month",
                "day",
                "hour",
            ],
            AggregatedChargesPeriod.DAY: [
                "year",
                "month",
                "day",
                "hour",
            ],
            AggregatedChargesPeriod.WEEK: [
                "year",
                "month",
                "day",
            ],
            AggregatedChargesPeriod.MONTH: [
                "year",
                "month",
                "day",
            ],
            AggregatedChargesPeriod.YEAR: [
                "year",
                "month",
            ],
        }
        return retval[periodicity]


@cache_results(timeout=60 * 60)  # one hour
def get_aggregated_charges(
    user_profile: UserProfile, periodicity: str = AggregatedChargesPeriod.HOUR, invalidate: bool = False
) -> list[dict[str, Any]]:
    """
    Query and aggregate resource usage charges for a user over a specified reporting interval.

    This function collects and summarizes charge records (e.g., tokens, cost) associated with
    a user’s resource locator, grouping by the appropriate fields for the requested
    periodicity (hourly, daily, weekly, etc.). The result is suitable for data visualization
    on usage charts. Results are cached to improve performance on repeated requests.

    Parameters
    ----------
    user_profile : UserProfile
        The user profile whose charges should be aggregated.
    periodicity : str, optional
        Key for aggregation period, accepted values are constants defined in
        :class:`AggregatedChargesPeriod` (default is ``AggregatedChargesPeriod.HOUR``).
    invalidate : bool, optional
        If True, bypass and invalidate any cached value before recomputing the result
        (default is False).

    Returns
    -------
    list of dict
        A list of dictionaries representing aggregated charge data. Each dict contains
        groupby fields (year, month, day, etc.), `resource_locator`, and aggregated
        metrics: ``records``, ``prompt_tokens``, ``completion_tokens``,
        ``total_tokens``, and ``total_cost``.

    Raises
    ------
    ValueError
        If the supplied periodicity value is unrecognized.

    Examples
    --------
    ::

        data = get_aggregated_charges(user_profile, periodicity="1_month")
        for entry in data:
            print(entry["total_cost"])
    """

    logger.debug(
        "%s.get_aggregated_charges() called with invalidate=%s for user_profile_id=%s",
        logger_prefix,
        invalidate,
        user_profile,
    )
    resource_locator = user_profile.record_locator
    start_date = datetime.now().astimezone()
    end_date = AggregatedChargesPeriod.delta(periodicity=periodicity)
    group_fields = AggregatedChargesPeriod.grouping_fields(periodicity)
    start_q = (
        Q(year__gt=start_date.year)
        | (Q(year=start_date.year) & Q(month__gt=start_date.month))
        | (Q(year=start_date.year) & Q(month=start_date.month) & Q(day__gt=start_date.day))
        | (Q(year=start_date.year) & Q(month=start_date.month) & Q(day=start_date.day) & Q(hour__gte=start_date.hour))
    )

    end_q = (
        Q(year__lt=end_date.year)
        | (Q(year=end_date.year) & Q(month__lt=end_date.month))
        | (Q(year=end_date.year) & Q(month=end_date.month) & Q(day__lt=end_date.day))
        | (Q(year=end_date.year) & Q(month=end_date.month) & Q(day=end_date.day) & Q(hour__lte=end_date.hour))
    )

    retval = (
        AggregatedCharges.objects.filter(resource_locator=resource_locator)
        .filter(start_q & end_q)
        .values(
            *group_fields,
            "resource_locator",
        )
        .annotate(
            records=Sum("records"),
            prompt_tokens=Sum("prompt_tokens"),
            completion_tokens=Sum("completion_tokens"),
            total_tokens=Sum("total_tokens"),
            total_cost=Sum("total_cost"),
        )
        .order_by(
            *group_fields,
            "resource_locator",
        )
    )
    data = list(retval)
    logger.debug(
        "%s.get_aggregated_charges() retrieved and cached aggregated charges for %s: %s",
        logger_prefix,
        user_profile,
        data,
    )
    return data


class MyResourcesView(SmarterAuthenticatedWebView):
    """API view for the Aggregated Charges Chart React component on the dashboard."""

    @property
    def formatted_class_name(self) -> str:
        """Returns the class name in a formatted string along with the name of this view."""
        class_name = f"{__name__}.{MyResourcesView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, periodicity: str, *args, **kwargs) -> JsonResponse:

        user = get_resolved_user(request.user)
        user_profile = UserProfile.get_cached_object(user=user)  # type: ignore
        logger.debug("%s.post()", self.formatted_class_name)

        retval = get_aggregated_charges(user_profile=user_profile, periodicity=periodicity)
        return JsonResponse(retval, status=HTTPStatus.OK)
