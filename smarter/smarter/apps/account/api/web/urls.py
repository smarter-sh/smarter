"""
URL configuration for the Account app's endpoints in the web console's api.

These are mounted at ``/api/web/account/``. The Budget list page's React app calls the ones under
``/api/web/account/budget/``, and the single-page console calls the others, which sign in and out, sign
up, activate an account and reset a password. See :mod:`smarter.apps.api.web`, :mod:`smarter.apps.account.views.budget.listview`
and :mod:`smarter.apps.account.api.web.views`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path

from smarter.apps.account.api.web.data_export import (
    DataExportDetailView,
    DataExportView,
)
from smarter.apps.account.api.web.profile_image import ProfileImageView
from smarter.apps.account.api.web.user_profiles import (
    UserProfileSelectView,
    UserProfilesView,
)
from smarter.apps.account.api.web.views import (
    ActivateApiView,
    ActivationResendApiView,
    PasswordResetApiView,
    PasswordResetRequestApiView,
    SignInApiView,
    SignOutApiView,
    SignUpApiView,
)
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
    sign_in = to_snake_case(SignInApiView.__name__)
    sign_out = to_snake_case(SignOutApiView.__name__)
    sign_up = to_snake_case(SignUpApiView.__name__)
    activate = to_snake_case(ActivateApiView.__name__)
    activation_resend = to_snake_case(ActivationResendApiView.__name__)
    password_reset_request = to_snake_case(PasswordResetRequestApiView.__name__)
    password_reset = to_snake_case(PasswordResetApiView.__name__)
    profile_image = to_snake_case(ProfileImageView.__name__)
    data_export = to_snake_case(DataExportView.__name__)
    data_export_detail = to_snake_case(DataExportDetailView.__name__)
    user_profiles = to_snake_case(UserProfilesView.__name__)
    user_profile_select = to_snake_case(UserProfileSelectView.__name__)


urlpatterns = [
    path("login/", SignInApiView.as_view(), name=AccountApiWebReverseNames.sign_in),
    path("logout/", SignOutApiView.as_view(), name=AccountApiWebReverseNames.sign_out),
    path("register/", SignUpApiView.as_view(), name=AccountApiWebReverseNames.sign_up),
    path("activate/<uidb64>/<token>/", ActivateApiView.as_view(), name=AccountApiWebReverseNames.activate),
    path(
        "activation-resend/",
        ActivationResendApiView.as_view(),
        name=AccountApiWebReverseNames.activation_resend,
    ),
    path(
        "password-reset-request/",
        PasswordResetRequestApiView.as_view(),
        name=AccountApiWebReverseNames.password_reset_request,
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        PasswordResetApiView.as_view(),
        name=AccountApiWebReverseNames.password_reset,
    ),
    # the user menu's: see smarter.apps.account.api.web.profile_image, data_export and user_profiles.
    path("profile-image/", ProfileImageView.as_view(), name=AccountApiWebReverseNames.profile_image),
    path("data-export/", DataExportView.as_view(), name=AccountApiWebReverseNames.data_export),
    path(
        "data-export/<int:export_id>/",
        DataExportDetailView.as_view(),
        name=AccountApiWebReverseNames.data_export_detail,
    ),
    path("user-profiles/", UserProfilesView.as_view(), name=AccountApiWebReverseNames.user_profiles),
    path(
        "user-profiles/select/",
        UserProfileSelectView.as_view(),
        name=AccountApiWebReverseNames.user_profile_select,
    ),
    path("budget/listview/", BudgetListApiView.as_view(), name=AccountApiWebReverseNames.budget_listview),
    path(
        "budget/delete/<int:budget_id>/",
        BudgetListApiDeleteView.as_view(),
        name=AccountApiWebReverseNames.budget_delete,
    ),
]
