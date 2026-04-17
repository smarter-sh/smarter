"""
URLs for Smarter Api.
"""

from django.urls import include, path

from smarter.apps.api import urls as api_urls

urlpatterns = [
    path("", include(api_urls)),
]

__all__ = ["urlpatterns"]
