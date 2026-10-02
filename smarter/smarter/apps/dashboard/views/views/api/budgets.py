# pylint: disable=W0613
"""
Smarter.apps.dashboard.views.api.budgets
=========================================

API views for budget versus actual charts in the Smarter dashboard.

- :class:`BudgetsView`: the status of every budget that the user may see, now: each limit, the
  spending against it, and whether the resource is locked.
- :class:`BudgetSeriesView`: the budget versus the actual spending of each of the last billing
  periods of a resource, e.g. the last 12 months.

A user sees the budgets attached to themselves, and to the resources they own. Staff also see
those of their account, its members, and their resources. Superusers see every budget.
"""

from decimal import Decimal
from http import HTTPStatus
from typing import Any

from django.http import HttpRequest, JsonResponse

from smarter.apps.account.models import (
    ResourceConstraint,
    UserProfile,
    get_resolved_user,
)
from smarter.apps.account.models.budget import is_visible
from smarter.lib import logging
from smarter.lib.django.views import SmarterAuthenticatedWebView

logger = logging.getLogger(__name__)

DEFAULT_PERIODS = 12
MAX_PERIODS = 120


def _jsonable(data: dict[str, Any]) -> dict[str, Any]:
    """Decimals as numbers, for charts."""
    return {key: float(value) if isinstance(value, Decimal) else value for key, value in data.items()}


class BudgetsView(SmarterAuthenticatedWebView):
    """The status of every budget that the user may see."""

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        user_profile = UserProfile.get_cached_object(user=get_resolved_user(request.user))  # type: ignore
        constraints = ResourceConstraint.objects.filter(is_active=True).select_related("budget")
        retval = [
            _jsonable(constraint.status())
            for constraint in constraints
            if is_visible(user_profile, constraint.resource_locator)
        ]
        return JsonResponse(retval, status=HTTPStatus.OK, safe=False)


class BudgetSeriesView(SmarterAuthenticatedWebView):
    """
    The budget versus the actual spending of each of the last billing periods of a resource.

    ``?periods=N`` sets how many billing periods, 12 by default.
    """

    def post(self, request: HttpRequest, resource_locator: str, *args, **kwargs) -> JsonResponse:
        user_profile = UserProfile.get_cached_object(user=get_resolved_user(request.user))  # type: ignore
        if not is_visible(user_profile, resource_locator):
            return JsonResponse({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)
        try:
            periods = min(max(int(request.GET.get("periods", DEFAULT_PERIODS)), 1), MAX_PERIODS)
        except ValueError:
            return JsonResponse({"error": "periods must be an integer."}, status=HTTPStatus.BAD_REQUEST)
        constraints = ResourceConstraint.objects.filter(resource_locator=resource_locator).select_related("budget")
        retval = [
            {
                "status": _jsonable(constraint.status()),
                "series": [_jsonable(row) for row in constraint.series(periods=periods)],
            }
            for constraint in constraints
        ]
        return JsonResponse(retval, status=HTTPStatus.OK, safe=False)
