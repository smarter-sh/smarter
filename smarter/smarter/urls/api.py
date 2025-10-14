"""
URLs for Smarter Api.
"""

from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("", include("smarter.apps.api.urls")),
    #
    # superfluous stuff that breaks the site unless it's included ...
    # -----------
    path("admin/", admin.site.urls),
    path("", include("smarter.urls.console")),
]

__all__ = ["urlpatterns"]
