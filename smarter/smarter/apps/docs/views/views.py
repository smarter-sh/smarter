# pylint: disable=W0613
"""Django views."""

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.lib.django.views import SmarterWebHtmlView
from smarter.lib.typing import SmarterDictType

from ..utils import json_schema_path, manifest_path


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class ManifestsView(SmarterWebHtmlView):
    """Public Access Dashboard view."""

    template_path = "docs/manifests.html"

    def get(self, request, *args, **kwargs):
        """
        Render the list of every SAM kind's example manifest page, sorted by kind.

        :param request: The request.
        :returns: The rendered page.
        """

        def manifest(kind: str) -> SmarterDictType:
            return {
                "name": kind,
                "path": "/docs/" + manifest_path(kind),
            }

        manifests = [manifest(kind) for kind in SAMKinds.all()]
        manifests.sort(key=lambda m: m["name"])

        context = {"manifests": manifests}
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class JsonSchemasView(SmarterWebHtmlView):
    """Public Access Dashboard view."""

    template_path = "docs/json-schemas.html"

    def get(self, request, *args, **kwargs):
        """
        Render the list of every SAM kind's JSON Schema page, sorted by kind.

        :param request: The request.
        :returns: The rendered page.
        """

        def json_schema(kind: str) -> SmarterDictType:
            return {
                "name": kind,
                "path": "/docs/" + json_schema_path(kind),
            }

        schemas = [json_schema(kind) for kind in SAMKinds.all()]
        schemas.sort(key=lambda m: m["name"])
        context = {"schemas": schemas}
        return self.clean_http_response(request, template_path=self.template_path, context=context)
