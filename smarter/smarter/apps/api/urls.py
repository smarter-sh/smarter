"""URL configuration for smarter project."""

from django.urls import include, path
from django.views.generic import RedirectView


urlpatterns = [
    path("", RedirectView.as_view(url="/api/v1/", permanent=True)),
    path("v0/", include("smarter.apps.api.v0.urls")),
    path("v1/", include("smarter.apps.api.v1.urls")),
]
