"""URL configuration for dashboard legal pages."""

from django.urls import path

from smarter.common.utils import camel_case_object_name

from .const import namespace
from .profile import ProfileLanguageView, ProfileView

app_name = namespace


class ProfileReverseNames:
    """
    A class to hold the names of the profile views for easy reference throughout the codebase.
    """

    namespace = namespace

    profile_view = camel_case_object_name(ProfileView)
    language_view = camel_case_object_name(ProfileLanguageView)


urlpatterns = [
    path("", ProfileView.as_view(), name=ProfileReverseNames.profile_view),
    path("language/", ProfileLanguageView.as_view(), name=ProfileReverseNames.language_view),
]
