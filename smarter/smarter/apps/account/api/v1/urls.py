"""Account urls for smarter api"""

from django.urls import path

from .const import namespace
from .views.account import AccountListView, AccountView
from .views.account_contact import AccountContactListView, AccountContactView
from .views.batch_create_users import BatchCreateUsersView
from .views.user import UserListView, UserView

app_name = namespace


class Namespace:
    """Namespace for account api urls."""

    users_list_view = "account_users_list_view"
    user_view = "account_user_view"
    account_contact_list_view = "account_contact_list_view"
    account_contact_view = "account_contact_view"
    batch_create_users = "account_batch_create_users"


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
        name=Namespace.users_list_view,
    ),
    path(
        "users/<int:user_id>/",
        UserView.as_view(),
        name=Namespace.user_view,
    ),
    path(
        "contacts/",
        AccountContactListView.as_view(),
        name=Namespace.account_contact_list_view,
    ),
    path(
        "contacts/<int:account_contact_id>/",
        AccountContactView.as_view(),
        name=Namespace.account_contact_view,
    ),
    path(
        "batch-create-users/",
        BatchCreateUsersView.as_view(),
        name=Namespace.batch_create_users,
    ),
]
