"""
Views for the manifest drop zone page.

This module provides a view that renders a drag-and-drop interface allowing
authenticated users to upload a manifest file and apply it to the Smarter
platform.

Classes:
    ManifestDropZoneView: Renders the manifest drag-and-drop upload page.

Example:
    Wire up the view in your URL configuration::

        from smarter.apps.dashboard.views.apply_manifest.manifest_drop_zone import ManifestDropZoneView

        urlpatterns = [
            path("apply-manifest/", ManifestDropZoneView.as_view(), name="manifest-drop-zone"),
        ]
"""

from django.http import HttpRequest
from django.shortcuts import render

from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView


class ManifestDropZoneView(SmarterAuthenticatedNeverCachedWebView):
    """
    A simple view that renders a page with a manifest drop zone
    for plugin development.
    """

    template_path = "prompt/manifest-apply.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        return render(request, self.template_path, context={})
