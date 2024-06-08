"""Account API URL Configuration."""

from django.urls import include, path
from django.views.generic import RedirectView


urlpatterns = [
    path("", RedirectView.as_view(url="v1/")),
    path("v1/", include("smarter.apps.chat.api.v1.urls")),
]
