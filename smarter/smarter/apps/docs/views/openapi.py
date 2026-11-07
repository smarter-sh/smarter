"""
The OpenAPI page, and the OpenAPI document's earlier address, in the docs app.

The document itself is served by the api, at ``/api/v1/openapi.json``
(:mod:`smarter.apps.api.v1.contract.views`). The single-page console's OpenAPI page renders it with Scalar,
which the console ships. ``/docs/openapi.json``, the document's earlier address, redirects to the api's, so
that existing links and generated clients keep working.

Both are public: the document describes the api, and holds no data.
"""

from django.views.generic import RedirectView

from smarter.apps.api.v1.urls import ApiV1ReverseNames
from smarter.apps.dashboard.views.console_app import ConsoleAppView
from smarter.lib.django.shortcuts import reverse


class DocsOpenApiJsonView(RedirectView):
    """``/docs/openapi.json``: a permanent redirect to the api's document, ``/api/v1/openapi.json``."""

    permanent = True
    query_string = True

    def get_redirect_url(self, *args, **kwargs) -> str:
        """
        The api's document.

        :returns: Its path, ``/api/v1/openapi.json``, plus the request's query string.
        """
        self.url = reverse(ApiV1ReverseNames.namespace, ApiV1ReverseNames.openapi_json)
        return super().get_redirect_url(*args, **kwargs)


class DocsOpenApiView(ConsoleAppView):
    """``/docs/openapi/``: the console's page that renders the api's OpenAPI document with Scalar."""


__all__ = ["DocsOpenApiJsonView", "DocsOpenApiView"]
