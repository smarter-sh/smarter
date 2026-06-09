"""
URLs for Smarter Api.
"""

from django.urls import include, path

from smarter.apps.api import urls

urlpatterns = [
    path("", include(urls)),
]

__all__ = ["urlpatterns"]
