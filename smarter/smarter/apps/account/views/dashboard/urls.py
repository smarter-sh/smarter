"""
URL configuration for the account dashboard, mounted at ``/account/dashboard/``.

These are the urls of the user menu, the ``@smarter/dashboard-user-menu`` React
app: the profile image that it uploads, and the profiles that its Change Profile
item lists and chooses.
"""

from django.urls import path

from smarter.apps.account.const import namespace
from smarter.apps.account.views.dashboard.profile_image import ProfileImageView
from smarter.apps.account.views.dashboard.user_profiles import (
    UserProfileSelectView,
    UserProfilesView,
)
from smarter.common.utils import to_snake_case


class DashboardNamedUrls:
    """
    Holds the named url patterns of the account dashboard.

    The names are referenced with ``reverse()`` as ``account:<name>``.
    """

    namespace = namespace

    ACCOUNT_PROFILE_IMAGE = "dashboard_account_profile_image"
    ACCOUNT_USER_PROFILES = to_snake_case(UserProfilesView.__name__)
    ACCOUNT_USER_PROFILE_SELECT = to_snake_case(UserProfileSelectView.__name__)


urlpatterns = [
    path("profile-image/", ProfileImageView.as_view(), name=DashboardNamedUrls.ACCOUNT_PROFILE_IMAGE),
    path("user-profiles/", UserProfilesView.as_view(), name=DashboardNamedUrls.ACCOUNT_USER_PROFILES),
    path(
        "user-profiles/select/",
        UserProfileSelectView.as_view(),
        name=DashboardNamedUrls.ACCOUNT_USER_PROFILE_SELECT,
    ),
]
