"""Account urls for smarter api"""

from django.urls import path

from .const import namespace
from .views.account import AccountListView, AccountView
from .views.account_contact import AccountContactListView, AccountContactView
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
    path(
        "contacts/",
        AccountContactListView.as_view(),
        name="account_contact_list_view",
    ),
    path(
        "contacts/<int:account_contact_id>/",
        AccountContactView.as_view(),
        name="account_contact_view",
    ),
]
