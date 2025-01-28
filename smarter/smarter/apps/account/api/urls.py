"""Account API URL Configuration."""

from django.urls import include, path
from django.views.generic import RedirectView


urlpatterns = [
    path("", RedirectView.as_view(url="v1/", permanent=True)),
    path("v1/", include("smarter.apps.account.api.v1.urls")),
]
