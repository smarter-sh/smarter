"""Account API URL Configuration."""

from django.urls import include, path
from django.views.generic import RedirectView

from .const import namespace


app_name = namespace


urlpatterns = [
    path("", RedirectView.as_view(url="v1/", permanent=True)),
    path("v1/", include("smarter.apps.chat.api.v1.urls")),
]
