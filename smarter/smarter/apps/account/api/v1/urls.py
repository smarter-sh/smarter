"""Account urls for smarter api"""

from django.urls import path

from .views.account import AccountListView, AccountView
from .views.payment_methods import PaymentMethodsListView, PaymentMethodView
from .views.user import UserListView, UserView


urlpatterns = [
    # account
    # -----------------------------------------------------------------------
    path("<int:account_id>/", AccountView.as_view(), name="account_view"),
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
