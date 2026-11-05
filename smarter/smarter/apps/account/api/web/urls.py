"""
URL configuration for the Account app's endpoints in the web console's api.

These are mounted at ``/api/web/account/``. The Budget list page's React app calls the ones under
``/api/web/account/budget/``. See :mod:`smarter.apps.api.web` and
:mod:`smarter.apps.account.views.budget.listview`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path

from smarter.apps.account.const import namespace
from smarter.apps.account.views.budget.listview import (
    BudgetListApiDeleteView,
    BudgetListApiView,
)
from smarter.apps.api.web.const import path_namespace
from smarter.common.utils import to_snake_case

app_name = namespace


class AccountApiWebReverseNames:
    """
    Reverse view names for the Account app's endpoints in the web console's api.

    The ``budget_`` names are the Budget list page's endpoints.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(AccountApiWebReverseNames.namespace, AccountApiWebReverseNames.budget_listview)
    """

    namespace = f"{path_namespace}:{namespace}"

    budget_listview = to_snake_case(BudgetListApiView.__name__)
    budget_delete = to_snake_case(BudgetListApiDeleteView.__name__)


urlpatterns = [
    path("budget/listview/", BudgetListApiView.as_view(), name=AccountApiWebReverseNames.budget_listview),
    path(
        "budget/delete/<int:budget_id>/",
        BudgetListApiDeleteView.as_view(),
        name=AccountApiWebReverseNames.budget_delete,
    ),
]
