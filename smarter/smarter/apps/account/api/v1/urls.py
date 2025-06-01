"""Account urls for smarter api"""

from django.urls import path

from .const import namespace
from .views.account import AccountListView, AccountView
from .views.payment_methods import PaymentMethodsListView, PaymentMethodView
from .views.user import UserListView, UserView


app_name = namespace

urlpatterns = [
    path("", AccountListView.as_view(), name="account_list_view"),
    # account
    # -----------------------------------------------------------------------
    path("<int:account_id>/", AccountView.as_view(), name="account_view"),
    # account users
    # -----------------------------------------------------------------------
    path(
        "users/",
        UserListView.as_view(),
        name="account_users_list_view",
    ),
    path(
        "users/<int:user_id>/",
        UserView.as_view(),
        name="account_user_view",
    ),
    # account payment methods
    # -----------------------------------------------------------------------
    path(
        "payment-methods/",
        PaymentMethodsListView.as_view(),
        name="account_payment_methods_list_view",
    ),
    path(
        "payment-methods/<int:payment_method_id>/",
        PaymentMethodView.as_view(),
        name="account_payment_method_view",
    ),
]
