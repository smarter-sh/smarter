"""
Django URL patterns for the Budget web console.

how we got here:
 - /budget/
"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .detailview import BudgetDetailView
from .listview import BudgetListApiDeleteView, BudgetListApiView, BudgetListView

app_name = namespace


class BudgetReverseNames:
    """Named URL patterns of the Budget web console."""

    namespace = namespace

    detailview = to_snake_case(BudgetDetailView.__name__)
    listview = to_snake_case(BudgetListView.__name__)
    listview_api = to_snake_case(BudgetListApiView.__name__)
    listview_api_delete = to_snake_case(BudgetListApiDeleteView.__name__)


urlpatterns = [
    path("", BudgetListView.as_view(), name=BudgetReverseNames.listview),
    path("budgets/<str:hashed_id>/", BudgetDetailView.as_view(), name=BudgetReverseNames.detailview),
    path("react-integration/api/listview/", BudgetListApiView.as_view(), name=BudgetReverseNames.listview_api),
    path(
        "react-integration/api/delete/<int:budget_id>/",
        BudgetListApiDeleteView.as_view(),
        name=BudgetReverseNames.listview_api_delete,
    ),
]
