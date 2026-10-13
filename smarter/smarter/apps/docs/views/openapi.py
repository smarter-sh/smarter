"""
The Smarter api's OpenAPI document, and a page that renders it, in the docs app.

The document is the committed ``openapi.json`` of :mod:`smarter.apps.api.v1.contract`: the typed
OpenAPI 3.1 contract of the cli api, the chat api and the REST reads, from which clients and SDKs
are generated. It differs from the Swagger and Redoc pages, which drf-yasg generates from the
views, in OpenAPI 2, with untyped request and response bodies.

Both are public, as the Swagger page is: the document describes the api, and holds no data.
"""

import json

from django.http import HttpRequest, JsonResponse

from smarter.apps.api.v1.contract.const import OPENAPI_PATH
from smarter.lib.django.views import SmarterView, SmarterWebHtmlView
from smarter.lib.typing import SmarterDictType


def openapi_document(request: HttpRequest) -> SmarterDictType:
    """
    The committed OpenAPI document, whose first server is the platform that serves it.

    The committed document's servers are the default platform's and a local one. This platform's
    own ``/api/v1``, relative to the document's url, is added before them, so that a viewer's
    requests, e.g. Swagger UI's "Try it out", go to the platform that the reader is on.

    :param request: The request for the document.
    :type request: HttpRequest
    :returns: The document.
    :rtype: SmarterDictType
    """
    with open(OPENAPI_PATH, encoding="utf-8") as file:
        document = json.load(file)
    document["servers"] = [
        {"url": request.build_absolute_uri("/api/v1"), "description": "This platform."},
        *document.get("servers", []),
    ]
    return document


class DocsOpenApiJsonView(SmarterView):
    """The Smarter api's OpenAPI 3.1 document, as JSON."""

    def get(self, request: HttpRequest, *args, **kwargs):
        """Return the document."""
        return JsonResponse(openapi_document(request), json_dumps_params={"indent": 2})


class DocsOpenApiView(SmarterWebHtmlView):
    """A page that renders the Smarter api's OpenAPI document with Swagger UI, and links to it."""

    template_path = "docs/openapi.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        """Render the page."""
        return self.clean_http_response(request, template_path=self.template_path, context={})


__all__ = ["DocsOpenApiJsonView", "DocsOpenApiView", "openapi_document"]
