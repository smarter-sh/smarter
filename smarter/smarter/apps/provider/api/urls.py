"""Account API URL Configuration."""

from django.urls import include, path
from django.views.generic import RedirectView

from smarter.apps.provider.api.v1 import urls as provider_api_v1_urls

from .const import namespace
from .v1.const import namespace as v1_namespace

app_name = namespace


urlpatterns = [
    path("", RedirectView.as_view(url="v1/", permanent=True)),
    path("v1/", include(provider_api_v1_urls, namespace=v1_namespace)),
]
