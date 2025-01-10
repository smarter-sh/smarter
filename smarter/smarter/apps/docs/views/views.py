# pylint: disable=W0613
"""Django views"""


from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.lib.django.view_helpers import SmarterWebHtmlView

from ..utils import json_schema_path, manifest_path


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class ManifestsView(SmarterWebHtmlView):
    """Public Access Dashboard view"""

    template_path = "docs/manifests.html"

    def get(self, request, *args, **kwargs):

        def manifest(kind: str) -> dict:
            return {
                "name": kind,
                "path": "/docs/" + manifest_path(kind),
            }

        manifests = [manifest(kind) for kind in SAMKinds.all_values()]
        context = {"manifests": manifests}
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class JsonSchemasView(SmarterWebHtmlView):
    """Public Access Dashboard view"""

    template_path = "docs/json-schemas.html"

    def get(self, request, *args, **kwargs):

        def json_schema(kind: str) -> dict:
            return {
                "name": kind,
                "path": "/docs/" + json_schema_path(kind),
            }

        schemas = [json_schema(kind) for kind in SAMKinds.all_values()]
        context = {"schemas": schemas}
        return self.clean_http_response(request, template_path=self.template_path, context=context)
