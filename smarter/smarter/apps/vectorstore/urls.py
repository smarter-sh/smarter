"""
URL configuration for the vectorstore app.
"""

from django.urls import path

from smarter.apps.vectorstore.views import (
    VectorstoreListView,
    VectorstoreManifestView,
)

from .const import namespace

app_name = namespace


urlpatterns = [
    path("", VectorstoreListView.as_view(), name="list_view"),
    path(
        "vectorstores/<str:backend>/<str:name>/manifest/",
        VectorstoreManifestView.as_view(),
        name="manifest_view",
    ),
]
