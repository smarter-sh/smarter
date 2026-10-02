# pylint: disable=W0613
"""
Views of the React Budget list in the Smarter web console.

Budgets are managed by superusers, so the list shows superusers every budget, and others the
budgets that are attached to a resource that they may see, with only those resources. Each
resource shows its budget versus its actual spending, with the URL of its chart's data.
"""

from http import HTTPStatus
from typing import Any

from django.conf import settings
from django.core.handlers.asgi import ASGIRequest
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.urls import reverse as django_reverse

from smarter.apps.account.manifest.brokers.budget import resource_to_manifest
from smarter.apps.account.models import Budget, ResourceConstraint, UserProfile
from smarter.apps.account.models.budget import is_visible
from smarter.apps.account.serializers import BudgetSerializer, UserProfileSerializer
from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


def visible_constraints(user_profile: UserProfile, budget: Budget) -> list[ResourceConstraint]:
    """The budget's resources that the user may see."""
    constraints = budget.constraints.select_related("budget").order_by("resource_locator")  # type: ignore[attr-defined]
    if user_profile.user.is_superuser:
        return list(constraints)
    return [c for c in constraints if is_visible(user_profile, c.resource_locator)]


def budget_list_item(view: SmarterAuthenticatedNeverCachedWebView, budget: Budget, constraints) -> dict[str, Any]:
    """A budget, with the budget versus the actual spending of each of its resources."""
    # pylint: disable=C0415
    from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames

    series_name = f"dashboard:{DashboardApiReverseNames.namespace}:{DashboardApiReverseNames.budget_series}"
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


class BudgetListView(SmarterAuthenticatedNeverCachedWebView):
    """Render the Budget list of the Smarter web console."""

    template_path = "react/budget-list.html"

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        return self.formatted_text(f"{__name__}.{BudgetListView.__name__}[{id(self)}]")

    def get(self, request: ASGIRequest, *args, **kwargs):
        # pylint: disable=C0415
        from .urls import BudgetReverseNames

        context = {
            "budget_list": {
                "root_id": "smarter-budget-list-root",
                "django_csrf_cookie_name": settings.CSRF_COOKIE_NAME,
                "django_session_cookie_name": settings.SESSION_COOKIE_NAME,
                "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
                "budget_list_api_url": reverse(BudgetReverseNames.namespace, BudgetReverseNames.listview_api),
                "react_debug_mode": switch_is_active(SmarterWaffleSwitches.ENABLE_REACTAPP_DEBUG_MODE),
                "smarter_request_id": self.generate_smarter_request_id(),
            }
        }
        return render(request, template_name=self.template_path, context=context)


class BudgetListApiView(SmarterAuthenticatedNeverCachedWebView):
    """The budgets that the user may see, with the budget versus the actual spending of each of their resources."""

    @property
    def formatted_class_name(self) -> str:
        return self.formatted_text(f"{__name__}.{BudgetListApiView.__name__}[{id(self)}]")

    def post(self, request: ASGIRequest, *args, **kwargs) -> JsonResponse:
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
        return self.formatted_text(f"{__name__}.{BudgetListApiDeleteView.__name__}[{id(self)}]")

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        budget_id = kwargs.get("budget_id")
        if not self.user_profile or not self.user_profile.user.is_superuser:
            return JsonResponse({"error": "Only superusers may delete a budget."}, status=HTTPStatus.FORBIDDEN)
        budget = Budget.objects.filter(id=budget_id).first()
        if budget is None:
            return JsonResponse({"error": f"Budget with id {budget_id} not found."}, status=HTTPStatus.NOT_FOUND)
        budget.delete()
        logger.info("%s.post() deleted budget %s.", self.formatted_class_name, budget)
        return JsonResponse({"message": f"Budget with id {budget_id} deleted successfully."}, status=HTTPStatus.OK)
