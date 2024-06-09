"""URL configuration for smarter project."""

from django.urls import include, path
from django.views.generic import RedirectView


urlpatterns = [
    path("", RedirectView.as_view(url="/api/docs/", permanent=True)),
    path("docs/", include("smarter.apps.api.docs.urls")),
    path("v1/", include("smarter.apps.api.v1.urls")),
]
