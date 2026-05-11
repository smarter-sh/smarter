"""Account urls for smarter api"""

from django.urls import path

from smarter.common.utils import camel_case_object_name

from .const import namespace
from .views.account import AccountListView, AccountView
from .views.account_contact import AccountContactListView, AccountContactView
from .views.batch_create_users import BatchCreateUsersView
from .views.user import UserListView, UserView

app_name = namespace


class AccountAPINamespaces:
    """Namespace for account api urls."""

    users_list_view = camel_case_object_name(UserListView)
    user_view = camel_case_object_name(UserView)
    account_contact_list_view = camel_case_object_name(AccountContactListView)
    account_contact_view = camel_case_object_name(AccountContactView)
    batch_create_users = camel_case_object_name(BatchCreateUsersView)


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
        name=AccountAPINamespaces.users_list_view,
    ),
    path(
        "users/<int:user_id>/",
        UserView.as_view(),
        name=AccountAPINamespaces.user_view,
    ),
    path(
        "contacts/",
        AccountContactListView.as_view(),
        name=AccountAPINamespaces.account_contact_list_view,
    ),
    path(
        "contacts/<int:account_contact_id>/",
        AccountContactView.as_view(),
        name=AccountAPINamespaces.account_contact_view,
    ),
    path(
        "batch-create-users/",
        BatchCreateUsersView.as_view(),
        name=AccountAPINamespaces.batch_create_users,
    ),
]
