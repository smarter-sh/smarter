"""
API URLs for the Smarter platform.
"""

from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("", include("smarter.apps.api.urls")),
    path("admin/", admin.site.urls),
    path("", include("smarter.urls")),
]
