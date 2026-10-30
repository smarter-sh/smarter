# pylint: disable=W0613
"""
API view of a resource's detail, for the web console's resource lists.

When a row of a list is chosen, the list opens the resource's detail, whose Manifest, Hierarchy and
Dependencies tabs are fetched here, from the row's ``detailUrl``. See :mod:`smarter.apps.dashboard.resource_detail`.
"""

from http import HTTPStatus

from django.http import HttpRequest, JsonResponse

from smarter.apps.dashboard.resource_detail import resource_detail
from smarter.lib import logging
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView

logger = logging.getLogger(__name__)


class ResourceDetailView(SmarterAuthenticatedNeverCachedWebView):
    """
    Return the detail of a resource that the user may read: its manifest, what it uses, and what uses it.

    The url names the resource's SAM kind and its record locator. A resource that doesn't exist, that the
    user may not read, or that is not of the kind, is a 404.

    Response shape, a dumped :class:`~smarter.apps.dashboard.resource_detail.ResourceDetail`:

    .. code-block:: json

        {
            "kind": "Guardrail",
            "name": "pii_redaction",
            "recordLocator": "guardrail-rMTAwx",
            "url": "/guardrail/guardrails/rMTAwx/",
            "manifest": "apiVersion: smarter.sh/v1\\nkind: Guardrail\\n...",
            "manifestError": "",
            "tree": {"kind": "Guardrail", "name": "pii_redaction", "children": [...], ...},
            "dependents": [{"kind": "LLMClient", "name": "stackademy", "children": [], ...}]
        }

    **Example usage**::

        GET /dashboard/api/resource/Guardrail/guardrail-rMTAwx/
    """

    http_method_names = ["get", "post"]

    def get(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """Return the same json as a POST, so that the detail can be browsed."""
        return self.post(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Return the resource's detail.

        :param request: The request.
        :type request: django.http.HttpRequest
        :param kwargs: ``kind`` and ``record_locator``, from the url.
        :returns: The detail, or ``{"error": ...}``, a 404.
        :rtype: django.http.JsonResponse
        """
        kind = kwargs.get("kind", "")
        record_locator = kwargs.get("record_locator", "")
        detail = resource_detail(request, kind, record_locator)
        if detail is None:
            return JsonResponse({"error": f"{kind} not found."}, status=HTTPStatus.NOT_FOUND)
        logger.debug("%s.post() detail of %s %s", self.formatted_class_name, kind, record_locator)
        return JsonResponse(detail.model_dump(mode="json"), status=HTTPStatus.OK)
