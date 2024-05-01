"""Smarter API command-line interface URL configuration."""

from django.urls import path

from .views.apply import ApplyManifestApiView
from .views.delete import DeleteObjectApiView
from .views.get import GetObjectsApiView


urlpatterns = [
    path("", ApplyManifestApiView.as_view(), name="cli_default_view"),
    path("apply/", ApplyManifestApiView.as_view(), name="cli_apply_manifest_view"),
    path("get/", GetObjectsApiView.as_view(), name="cli_get_objects_view"),
    path("delete/", DeleteObjectApiView.as_view(), name="cli_get_objects_view"),
]
