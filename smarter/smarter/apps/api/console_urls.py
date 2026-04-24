"""URL configuration for smarter project."""

from django.urls import path

from smarter.common.utils import camel_case_object_name

from .const import namespace
from .views import ManifestDropZoneView

app_name = namespace

urlpatterns = [
    path(
        "",
        ManifestDropZoneView.as_view(),
        name=camel_case_object_name(ManifestDropZoneView),
    ),
]
