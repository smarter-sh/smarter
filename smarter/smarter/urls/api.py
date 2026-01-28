"""
URLs for Smarter Api.
"""

from django.urls import include, path

urlpatterns = [
    path("", include("smarter.apps.api.urls")),
]

__all__ = ["urlpatterns"]
