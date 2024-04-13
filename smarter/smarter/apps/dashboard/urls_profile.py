"""URL configuration for dashboard legal pages."""

from django.urls import path

from .views.profile import ProfileLanguageView, ProfileView


urlpatterns = [
    path("", ProfileView.as_view(), name="profile"),
    path("language/", ProfileLanguageView.as_view(), name="language"),
]
