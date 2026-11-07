"""
The page that renders the Smarter api's OpenAPI document, in the docs app.

The document itself is served by the api, at ``/api/v1/openapi.json``
(:mod:`smarter.apps.api.v1.contract.views`). The page renders it with Scalar, which is vendored in
``static/assets/plugins/custom/scalar/``. ``/docs/openapi.json``, the document's earlier address,
redirects to the api's, so that existing links and generated clients keep working.

Both are public: the document describes the api, and holds no data.
"""

from django.http import HttpRequest
from django.views.generic import RedirectView

from smarter.apps.api.v1.urls import ApiV1ReverseNames
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import SmarterWebHtmlView


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


class DocsOpenApiView(SmarterWebHtmlView):
    """A page that renders the Smarter api's OpenAPI document with Scalar, and links to it."""

    template_path = "docs/openapi.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        """Render the page."""
        context = {"openapi_json_url": reverse(ApiV1ReverseNames.namespace, ApiV1ReverseNames.openapi_json)}
        return self.clean_http_response(request, template_path=self.template_path, context=context)


__all__ = ["DocsOpenApiJsonView", "DocsOpenApiView"]
