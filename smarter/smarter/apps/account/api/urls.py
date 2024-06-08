"""Account API URL Configuration."""

from django.urls import include, path


urlpatterns = [
    path("", include("smarter.apps.account.api.v1.urls")),
    path("v1/", include("smarter.apps.account.api.v1.urls")),
]
