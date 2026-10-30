# pylint: disable=W0613
"""
API view of the dashboard's global search.

The dashboard's search box posts its query here, and shows the resources of every kind that match
it and that the user may read, grouped by list. See :mod:`smarter.apps.dashboard.search`.
"""

import json
from http import HTTPStatus

from django.http import HttpRequest, JsonResponse

from smarter.apps.account.models import get_resolved_user
from smarter.apps.dashboard.search import GlobalSearchResponse, global_search
from smarter.lib import logging
from smarter.lib.django.views import SmarterAuthenticatedWebView

logger = logging.getLogger(__name__)


class GlobalSearchView(SmarterAuthenticatedWebView):
    """
    Search every list of the web console.

    The query is the ``query`` of the json request body, e.g. ``{"query": "tag:production"}``, or the
    ``query`` query parameter of a GET.

    Response shape, a dumped :class:`~smarter.apps.dashboard.search.GlobalSearchResponse`:

    .. code-block:: json

        {
            "query": "tag:production",
            "mode": "tag",
            "error": "",
            "count": 3,
            "groups": [
                {
                    "label": "Guardrails",
                    "count": 3,
                    "url": "/guardrail/?tag=production",
                    "results": [{"name": "pii_redaction", "description": "...", "url": "/guardrail/guardrails/rMTAwx/"}]
                }
            ]
        }
    """

    def query_of(self, request: HttpRequest) -> str:
        """Return the query, from the json body, or the query parameters."""
        try:
            body = json.loads(request.body or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = {}
        query = body.get("query") if isinstance(body, dict) else None
        if not isinstance(query, str):
            query = request.GET.get("query", "")
        return query

    def get(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """Return the same json as a POST, so that the search can be browsed."""
        return self.post(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """Return the resources that match the query, grouped by list."""
        user = get_resolved_user(request.user)
        query = self.query_of(request)
        if user is None:
            return JsonResponse(GlobalSearchResponse(query=query).model_dump(mode="json"), status=HTTPStatus.OK)
        logger.debug("%s.post() query=%s user=%s", self.formatted_class_name, query, user.username)
        response = global_search(user, query)
        return JsonResponse(response.model_dump(mode="json"), status=HTTPStatus.OK)
