"""Django URL patterns connection app API endpoints."""

from django.urls import include, path
from django.views.generic import RedirectView

from smarter.apps.connection.api.v1 import urls as connection_v1_urls

from .const import namespace
from .v1.const import namespace as v1_namespace

app_name = namespace

urlpatterns = [
    path("", RedirectView.as_view(url="v1/")),
    path("v1", include(connection_v1_urls, namespace=v1_namespace)),
]
