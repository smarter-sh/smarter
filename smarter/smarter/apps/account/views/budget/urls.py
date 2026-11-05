"""
Django URL patterns for the Budget web console.

how we got here:
 - /budget/
"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .detailview import BudgetDetailView
from .listview import BudgetListView

app_name = namespace


class BudgetReverseNames:
    """
    Named URL patterns of the Budget web console's pages.

    The endpoints that the list page's React app calls are in the web console's api:
    see :class:`smarter.apps.account.api.web.urls.AccountApiWebReverseNames`.
    """

    namespace = namespace

    detailview = to_snake_case(BudgetDetailView.__name__)
    listview = to_snake_case(BudgetListView.__name__)


urlpatterns = [
    path("", BudgetListView.as_view(), name=BudgetReverseNames.listview),
    path("budgets/<str:hashed_id>/", BudgetDetailView.as_view(), name=BudgetReverseNames.detailview),
]
