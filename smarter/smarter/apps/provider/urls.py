"""
Django URL patterns for the chatapp

how we got here:
 - /providers/api/v1/

"""

from django.urls import include, path

from .api.const import namespace as api_namespace
from .const import namespace


app_name = namespace

urlpatterns = [
    path("api/", include("smarter.apps.provider.api.urls", namespace=api_namespace)),
]
