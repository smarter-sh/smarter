"""URL configuration for dashboard legal pages."""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .profile import ProfileLanguageView, ProfileView

app_name = namespace


class ProfileReverseNames:
    """
    A class to hold the names of the profile views for easy reference throughout the codebase.
    """

    namespace = namespace

    profile_view = to_snake_case(ProfileView)
    language_view = to_snake_case(ProfileLanguageView)


urlpatterns = [
    path("", ProfileView.as_view(), name=ProfileReverseNames.profile_view),
    path("language/", ProfileLanguageView.as_view(), name=ProfileReverseNames.language_view),
]
