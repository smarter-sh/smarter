"""URL configuration for the web platform."""

from django.urls import path

from smarter.apps.dashboard.views.views.api.activity import ActivityView
from smarter.apps.dashboard.views.views.api.budgets import (
    BudgetSeriesView,
    BudgetsView,
)
from smarter.apps.dashboard.views.views.api.charges import ChargesView
from smarter.apps.dashboard.views.views.api.getting_started import GettingStartedView
from smarter.apps.dashboard.views.views.api.my_resources import MyResourcesView
from smarter.apps.dashboard.views.views.api.quick_actions import QuickActionsView
from smarter.apps.dashboard.views.views.api.service_health import ServiceHealthView
from smarter.common.utils import to_snake_case
from smarter.lib import logging

from .const import namespace

logger = logging.getLogger(__name__)

app_name = namespace


class DashboardApiReverseNames:
    """A class to hold the names of the dashboard views for easy reference throughout the codebase."""

    namespace = namespace

    my_resources = to_snake_case(MyResourcesView.__name__)
    service_health = to_snake_case(ServiceHealthView.__name__)
    token_charges = to_snake_case(ChargesView.__name__)
    budgets = to_snake_case(BudgetsView.__name__)
    budget_series = to_snake_case(BudgetSeriesView.__name__)
    activity = to_snake_case(ActivityView.__name__)
    getting_started = to_snake_case(GettingStartedView.__name__)
    quick_actions = to_snake_case(QuickActionsView.__name__)


urlpatterns = [
    path("my-resources/", MyResourcesView.as_view(), name=DashboardApiReverseNames.my_resources),
    path("service-health/", ServiceHealthView.as_view(), name=DashboardApiReverseNames.service_health),
    path("charges/<str:periodicity>/", ChargesView.as_view(), name=DashboardApiReverseNames.token_charges),
    path("budgets/", BudgetsView.as_view(), name=DashboardApiReverseNames.budgets),
    path(
        "budgets/<str:resource_locator>/series/",
        BudgetSeriesView.as_view(),
        name=DashboardApiReverseNames.budget_series,
    ),
    path("activity/", ActivityView.as_view(), name=DashboardApiReverseNames.activity),
    path("getting-started/", GettingStartedView.as_view(), name=DashboardApiReverseNames.getting_started),
    path("quick-actions/", QuickActionsView.as_view(), name=DashboardApiReverseNames.quick_actions),
]
