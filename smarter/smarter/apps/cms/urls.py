"""URL configuration for smarter project."""

from django.urls import include, path
from wagtail.admin import urls as wagtailadmin_urls
from wagtail_transfer import urls as wagtailtransfer_urls


urlpatterns = [
    path("admin/wagtail-transfer/", include(wagtailtransfer_urls)),
    path("admin/", include(wagtailadmin_urls)),
]
