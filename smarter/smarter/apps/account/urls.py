# -*- coding: utf-8 -*-
"""Account urls for smarter api"""

from django.urls import path
from django.views.decorators.http import require_http_methods

from smarter.apps.account.views.account import account_view, accounts_list_view


urlpatterns = [
    path("account/", require_http_methods(["GET", "POST", "PATCH", "DELETE"])(account_view), name="account_view"),
    path("accounts/", require_http_methods(["GET"])(accounts_list_view), name="accounts_list_view"),
    path(
        "accounts/<int:account_id>/",
        require_http_methods(["GET", "POST", "PATCH", "DELETE"])(account_view),
        name="plugins_view",
    ),
]
