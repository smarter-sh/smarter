"""
Views for the manifest drop zone page, which is a simple page that allows users
to drag-and-drop a manifest file in order to apply it to the Smarter platform.
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
