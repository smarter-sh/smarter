"""Secret API URL Configuration."""

from django.urls import include, path
from django.views.generic import RedirectView

from smarter.apps.secret.api.const import namespace
from smarter.apps.secret.api.v1 import urls as v1_urls
from smarter.apps.secret.api.v1.const import namespace as v1_namespace

app_name = namespace

urlpatterns = [
    path("", RedirectView.as_view(url="v1/", permanent=True)),
    path("v1/", include(v1_urls, namespace=v1_namespace)),
]
