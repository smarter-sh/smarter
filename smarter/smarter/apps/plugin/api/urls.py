"""Django URL patterns for the Chat"""

from django.urls import include, path
from django.views.generic import RedirectView

from smarter.apps.plugin.api.v1 import urls as v1_urls

from .const import namespace
from .v1.const import namespace as v1_namespace

app_name = namespace

urlpatterns = [
    path("", RedirectView.as_view(url="v1/")),
    path("v1", include(v1_urls, namespace=v1_namespace)),
]
