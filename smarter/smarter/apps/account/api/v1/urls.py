"""Account urls for smarter api"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.account import AccountListView, AccountView
from .views.account_contact import AccountContactListView, AccountContactView
from .views.batch_create_users import BatchCreateUsersView
from .views.user import UserListView, UserView
from .views.user_profile import UserProfileListView, UserProfileView

app_name = namespace


class AccountAPINamespaces:
    """Namespace for account api urls."""

    account_view = to_snake_case(AccountView)
    account_list_view = to_snake_case(AccountListView)
    users_list_view = to_snake_case(UserListView)
    user_view = to_snake_case(UserView)
    account_contact_list_view = to_snake_case(AccountContactListView)
    account_contact_view = to_snake_case(AccountContactView)
    batch_create_users = to_snake_case(BatchCreateUsersView)
    user_profile_list_view = to_snake_case(UserProfileListView)
    user_profile_view = to_snake_case(UserProfileView)


urlpatterns = [
    path("", AccountListView.as_view(), name=AccountAPINamespaces.account_list_view),
    # account
    # -----------------------------------------------------------------------
    path("<int:account_id>/", AccountView.as_view(), name=AccountAPINamespaces.account_view),
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
    path(
        "user-profiles/",
        UserProfileListView.as_view(),
        name=AccountAPINamespaces.user_profile_list_view,
    ),
    path(
        "user-profiles/<int:user_profile_id>/",
        UserProfileView.as_view(),
        name=AccountAPINamespaces.user_profile_view,
    ),
]
