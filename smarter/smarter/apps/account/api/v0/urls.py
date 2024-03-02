# -*- coding: utf-8 -*-
"""Account urls for smarter api"""

from django.urls import path
from django.views.decorators.http import require_http_methods

from smarter.apps.account.api.v0.views.account import account_view, accounts_list_view
from smarter.apps.account.api.v0.views.payment_methods import (
    payment_method_view,
    payment_methods_list_view,
)
from smarter.apps.plugin.api.v0.views import add_plugin_examples

from .views.user import user_view


urlpatterns = [
    # account
    # -----------------------------------------------------------------------
    path("", require_http_methods(["GET", "POST", "PATCH", "DELETE"])(account_view), name="account_view"),
    # account users
    # -----------------------------------------------------------------------
    path("users/", require_http_methods(["GET", "POST", "PATCH", "DELETE"])(user_view), name="user_view"),
    path(
        "users/<int:user_id>/add-example-plugins/",
        require_http_methods(["GET", "POST"])(add_plugin_examples),
        name="add_plugin_examples",
    ),
    path(
        "users/<int:user_id>/",
        require_http_methods(["GET", "POST", "PATCH", "DELETE"])(user_view),
        name="user_view",
    ),
    # account payment methods
    # -----------------------------------------------------------------------
    path(
        "payment-methods/<int:payment_method_id>/",
        require_http_methods(["GET", "POST", "PATCH", "DELETE"])(payment_method_view),
        name="payment_method_view",
    ),
    path(
        "payment-methods/",
        require_http_methods(["GET"])(payment_methods_list_view),
        name="payment_methods_list_view",
    ),
    path("", require_http_methods(["GET"])(accounts_list_view), name="accounts_list_view"),
    path(
        "<int:account_id>/",
        require_http_methods(["GET", "POST", "PATCH", "DELETE"])(account_view),
        name="plugins_view",
    ),
]
