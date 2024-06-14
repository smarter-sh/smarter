"""URL configuration for Smarter Api and web console."""

from django.urls import include, path, re_path
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls


urlpatterns = [
    # wagail urls
    # -----------------------------------
    path("admin/", include(wagtailadmin_urls)),
    re_path(r"", include(wagtail_urls)),
]
