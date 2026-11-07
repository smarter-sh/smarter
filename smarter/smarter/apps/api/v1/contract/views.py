"""
The Smarter api's OpenAPI document, ``GET /api/v1/openapi.json``.

The document is the committed ``openapi.json`` of :mod:`smarter.apps.api.v1.contract`: the typed
OpenAPI 3.1 contract of the cli api, the chat api and the REST reads, from which clients and SDKs
are generated. The web console's OpenAPI page renders it with Scalar, and ``/docs/openapi.json``,
its earlier address, redirects here.

It is public: the document describes the api, and holds no data.
"""

import json

from django.http import HttpRequest, JsonResponse

from smarter.apps.api.v1.contract.const import OPENAPI_PATH
from smarter.lib.django.views import SmarterView
from smarter.lib.typing import SmarterDictType


def openapi_document(request: HttpRequest) -> SmarterDictType:
    """
    The committed OpenAPI document, whose first server is the platform that serves it.

    The committed document's servers are the default platform's and a local one. This platform's
    own ``/api/v1``, relative to the document's url, is added before them, so that a viewer's
    requests, e.g. Scalar's "Test Request", go to the platform that the reader is on.

    :param request: The request for the document.
    :type request: HttpRequest
    :returns: The document.
    :rtype: SmarterDictType
    """
    with open(OPENAPI_PATH, encoding="utf-8") as file:
        document = json.load(file)
    this_platform = {"url": request.build_absolute_uri("/api/v1"), "description": "This platform."}
    committed_servers = document.get("servers", [])
    document["servers"] = [this_platform, *committed_servers]
    return document


class ApiV1OpenApiJsonView(SmarterView):
    """The Smarter api's OpenAPI 3.1 document, as JSON."""

    def get(self, request: HttpRequest, *args, **kwargs):
        """
        Return the document.

        :param request: The request.
        :returns: The document, indented, as JSON.
        """
        document = openapi_document(request)
        return JsonResponse(document, json_dumps_params={"indent": 2})


__all__ = ["ApiV1OpenApiJsonView", "openapi_document"]
