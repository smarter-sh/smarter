"""
URL configuration for the vectorstore app.
"""

from django.urls import include, path

from smarter.apps.vectorstore.api import urls as api_urls
from smarter.apps.vectorstore.views import (
    VectorstoreListView,
    VectorstoreManifestView,
)

from .api.const import namespace as api_namespace
from .const import namespace

app_name = namespace


urlpatterns = [
    path("", VectorstoreListView.as_view(), name="list_view"),
    path("api/", include(api_urls, namespace=api_namespace)),
    path(
        "vectorstores/<str:backend>/<str:name>/manifest/",
        VectorstoreManifestView.as_view(),
        name="manifest_view",
    ),
]
