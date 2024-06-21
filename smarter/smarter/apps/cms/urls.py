"""URL configuration for smarter project."""

from django.urls import include, path
from wagtail.admin import urls as wagtailadmin_urls


urlpatterns = [
    path("admin/", include(wagtailadmin_urls)),
]
