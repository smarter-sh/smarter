"""
The docs pages: the example manifests and the JSON Schemas of the SAM kinds, which the single-page console shows.

Each answers with the console's page (:class:`~smarter.apps.dashboard.views.console_app.ConsoleAppView`), and
the console reads what it shows from the api: the kinds from the session (``samKinds``), and a kind's example
manifest and JSON Schema from the public cli api, ``/api/v1/cli/example-manifest/<kind>/`` and
``/api/v1/cli/json-schema/<kind>/``. They are public, as that api is.
"""

from django.http import Http404, HttpRequest, HttpResponse

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.dashboard.views.console_app import ConsoleAppView


def is_sam_kind(kind: str) -> bool:
    """
    Whether a url's kind is a SAM kind, in any case: the docs' urls are lower case, e.g. ``llmclient``.

    :param kind: The kind, e.g. ``llmclient`` or ``LLMClient``.
    :returns: True for a SAM kind.
    """
    kinds = [name.lower() for name in SAMKinds.all()]
    return kind.lower() in kinds


class DocsExampleManifestsView(ConsoleAppView):
    """``/docs/manifests/``: what a manifest is, and a link to each kind's example manifest."""


class DocsJsonSchemasView(ConsoleAppView):
    """``/docs/json-schemas/``: what the JSON Schemas are for, and a link to each kind's."""


class DocsKindView(ConsoleAppView):
    """A docs page of one SAM kind, which answers 404 for a kind that doesn't exist."""

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Return the console's page, for a SAM kind.

        :param request: The request.
        :returns: The console's page.
        :raises Http404: For a kind that isn't a SAM kind.
        """
        kind = kwargs.get("kind", "")
        if not is_sam_kind(kind):
            raise Http404(f"{kind} is not a kind of Smarter resource.")
        return super().get(request, *args, **kwargs)


class DocsExampleManifestView(DocsKindView):
    """``/docs/manifest/<kind>/``: a kind's example manifest, as YAML."""


class DocsJsonSchemaView(DocsKindView):
    """``/docs/json-schema/<kind>/``: the JSON Schema of a kind's manifest."""


__all__ = [
    "DocsExampleManifestView",
    "DocsExampleManifestsView",
    "DocsJsonSchemaView",
    "DocsJsonSchemasView",
    "DocsKindView",
    "is_sam_kind",
]
