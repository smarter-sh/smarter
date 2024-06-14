"""URL configuration for Smarter Api and web console."""

from django.urls import include, path, re_path
from django.views.generic import RedirectView
from wagtail import urls as wagtail_urls


urlpatterns = [
    path("", RedirectView.as_view(url="/docs/")),
    re_path(r"", include(wagtail_urls)),
]
