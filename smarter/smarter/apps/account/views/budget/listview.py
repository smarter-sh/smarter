# pylint: disable=W0613
"""
Views of the React Budget list in the Smarter web console.

Budgets are managed by superusers, so the list shows superusers every budget, and others the
budgets that are attached to a resource that they may see, with only those resources. Each
resource shows its budget versus its actual spending, with the URL of its chart's data.
"""

from http import HTTPStatus
from typing import Optional

from django.core.handlers.asgi import ASGIRequest
from django.http import HttpRequest, JsonResponse
from django.urls import reverse as django_reverse

from smarter.apps.account.manifest.brokers.budget import resource_to_manifest
from smarter.apps.account.models import Budget, ResourceConstraint, UserProfile
from smarter.apps.account.models.budget import is_visible
from smarter.apps.account.serializers import BudgetSerializer, UserProfileSerializer
from smarter.apps.dashboard.views.console_app import ConsoleAppView
from smarter.lib import logging
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


def visible_constraints(user_profile: UserProfile, budget: Budget) -> list[ResourceConstraint]:
    """
    The budget's resources that the user may see.

    :param user_profile: The UserProfile of the user.
    :param budget: The Budget.
    :returns: Its ResourceConstraints, ordered by resource locator; all of them for a superuser.
    """
    constraints = budget.constraints.select_related("budget").order_by("resource_locator")  # type: ignore[attr-defined]
    if user_profile.user.is_superuser:
        return list(constraints)
    return [c for c in constraints if is_visible(user_profile, c.resource_locator)]


def budget_list_item(view: SmarterAuthenticatedNeverCachedWebView, budget: Budget, constraints) -> SmarterDictType:
    """
    A budget, with the budget versus the actual spending of each of its resources.

    :param view: The view, which converts each resource's status to camelCase.
    :param budget: The Budget.
    :param constraints: The Budget's ResourceConstraints to include.
    :returns: The serialized Budget, with ``resourceStatus``: each resource's status, manifest and
        the url of its spending series.
    """
    # pylint: disable=C0415
    from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames

    series_name = f"{DashboardApiReverseNames.namespace}:{DashboardApiReverseNames.budget_series}"
    resources = []
    for constraint in constraints:
        status = {
            key: float(value) if hasattr(value, "as_tuple") else value for key, value in constraint.status().items()
        }
        status["resource"] = resource_to_manifest(constraint.resource_locator)
        status["series_url"] = django_reverse(series_name, kwargs={"resource_locator": constraint.resource_locator})
        resources.append(view.to_camel_case(status))
    retval = dict(BudgetSerializer(budget).data)
    retval["resourceStatus"] = resources
    return retval


class BudgetListView(ConsoleAppView):
    """
    The Budget list page, ``/budget/``, which the single-page console serves (ADR-035).

    The console renders ``@smarter/budget-list``'s list at the page's path, and the list calls
    :class:`BudgetListApiView`, which applies the superuser rules above.
    """


class BudgetListApiView(SmarterAuthenticatedNeverCachedWebView):
    """The budgets that the user may see, with the budget versus the actual spending of each of their resources."""

    @property
    def formatted_class_name(self) -> str:
        """The class name, with the instance id, formatted for log messages."""
        return f"{self.formatted_text(__name__)}.{BudgetListApiView.__name__}[{id(self)}]"

    def post(self, request: ASGIRequest, *args, **kwargs) -> JsonResponse:
        """
        Return the budgets that the user may see, with their resources.

        A superuser sees every budget; anyone else, the budgets attached to a resource they may see.

        :param request: The request.
        :returns: The user, whether they are a superuser, and the budgets, as json.
        """
        user_profile: UserProfile = self.user_profile  # type: ignore[assignment]
        objects = []
        for budget in Budget.objects.order_by("name"):
            constraints = visible_constraints(user_profile, budget)
            if constraints or user_profile.user.is_superuser:
                objects.append(budget_list_item(self, budget, constraints))
        retval = {
            "user": UserProfileSerializer(user_profile).data,
            "isSuperuser": user_profile.user.is_superuser,
            "objects": objects,
        }
        return JsonResponse(retval)


class BudgetListApiDeleteView(SmarterAuthenticatedNeverCachedWebView):
    """Delete a budget, which detaches it from its resources and removes their locks.

    Superusers only.
    """

    @property
    def formatted_class_name(self) -> str:
        """The class name, with the instance id, formatted for log messages."""
        return f"{self.formatted_text(__name__)}.{BudgetListApiDeleteView.__name__}[{id(self)}]"

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Delete a Budget.

        Only a superuser may.

        :param request: The request.
        :param kwargs: ``budget_id``, the Budget's id.
        :returns: A json response: 200, 403 or 404.
        """
        budget_id = kwargs.get("budget_id")
        if not self.user_profile or not self.user_profile.user.is_superuser:
            return JsonResponse({"error": "Only superusers may delete a budget."}, status=HTTPStatus.FORBIDDEN)
        budget: Optional[Budget] = None
        if budget_id is not None:
            budget = Budget.objects.filter(id=budget_id).first()
        if budget is None:
            return JsonResponse({"error": f"Budget with id {budget_id} not found."}, status=HTTPStatus.NOT_FOUND)
        budget.delete()
        logger.info("%s.post() deleted budget %s.", self.formatted_class_name, budget)
        return JsonResponse({"message": f"Budget with id {budget_id} deleted successfully."}, status=HTTPStatus.OK)
