# pylint: disable=W0613
"""
Provider API view for the Dashboard prompt passthrough feature.

This module exposes a JSON API endpoint used by the prompt passthrough React
frontend to retrieve the LLM providers that the currently authenticated user
has read permission for. The provider list is serialised with
:class:`~smarter.apps.provider.serializers.ProviderMiniSerializer` and
returned as a JSON response.

Classes:
    ProviderApiView: Authenticated API view that returns the list of accessible
        LLM providers for the requesting user.

Example:
    Wire up the view in your URL configuration::

        from smarter.apps.dashboard.views.passthrough.api.providers import ProviderApiView

        urlpatterns = [
            path("providers/", ProviderApiView.as_view(), name="api_providers"),
        ]
"""

import logging

from django.http import HttpRequest, JsonResponse

from smarter.apps.account.models import get_resolved_user
from smarter.apps.provider.models import Provider
from smarter.apps.provider.serializers import ProviderMiniSerializer
from smarter.lib.django.views import (
    SmarterAuthenticatedNeverCachedWebView,
)

logger = logging.getLogger(__name__)


class ProviderApiView(SmarterAuthenticatedNeverCachedWebView):
    """
    Authenticated JSON API view that returns LLM providers accessible to the requesting user.

    Extends :class:`~smarter.lib.django.views.SmarterAuthenticatedNeverCachedWebView`
    to enforce authentication and prevent response caching.

    On a ``POST`` request the view resolves the authenticated user via
    :func:`~smarter.apps.account.models.get_resolved_user`, queries
    :class:`~smarter.apps.provider.models.Provider` for all records the user
    has read permission for, and returns them serialised as a JSON object.

    Response shape:

    .. code-block:: json

        {
            "providers": [
                {
                    "id": 1,
                    "name": "OpenAI",
                    "base_url": "https://api.openai.com/v1"
                }
            ]
        }

    Additional provider objects may appear in the ``providers`` array.
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to retrieve LLM providers accessible to the authenticated user.

        :param request: The incoming HTTP POST request from the client.
        :type request: django.http.HttpRequest
        :param args: Additional positional arguments forwarded by the URL dispatcher.
        :param kwargs: Additional keyword arguments forwarded by the URL dispatcher.
        :returns: A JSON response containing the list of accessible LLM providers.
        :rtype: django.http.JsonResponse
        """
        user = get_resolved_user(request.user)

        providers = Provider.objects.with_read_permission_for(user=user)  # type: ignore
        serialized_providers = ProviderMiniSerializer(providers, many=True).data
        return JsonResponse({"providers": serialized_providers})
