# -*- coding: utf-8 -*-
"""Account urls for smarter api"""

from django.urls import path
from django.views.decorators.http import require_http_methods

from smarter.apps.account.api.v0.views.account import AccountListView, AccountView
from smarter.apps.account.api.v0.views.payment_methods import (
    PaymentMethodsListView,
    PaymentMethodView,
)
from smarter.apps.plugin.api.v0.views import add_plugin_examples

from .views.user import UserListView, UserView


urlpatterns = [
    # account
    # -----------------------------------------------------------------------
    path("<str:account_number>/", AccountView.as_view(), name="account_view"),
    path("", AccountListView.as_view(), name="accounts_list_view"),
    # account users
    # -----------------------------------------------------------------------
    path(
        "users/",
        UserListView.as_view(),
        name="user_list_view",
    ),
    path(
        "users/<int:user_id>/",
        UserView.as_view(),
        name="user_view",
    ),
    path(
        "users/<int:user_id>/add-example-plugins/",
        require_http_methods(["GET", "POST"])(add_plugin_examples),
        name="add_plugin_examples",
    ),
    # account payment methods
    # -----------------------------------------------------------------------
    path(
        "payment-methods/",
        PaymentMethodsListView.as_view(),
        name="payment_methods_list_view",
    ),
    path(
        "payment-methods/<int:payment_method_id>/",
        PaymentMethodView.as_view(),
        name="payment_method_view",
    ),
]
