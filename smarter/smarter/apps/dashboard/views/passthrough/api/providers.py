# pylint: disable=W0613
"""
Provider API view for the Dashboard prompt passthrough feature.
Returns a list of LLM providers that the user has access to.
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
    API view to handle provider-related requests.
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        user = get_resolved_user(request.user)

        providers = Provider.objects.with_read_permission_for(user=user)  # type: ignore
        serialized_providers = ProviderMiniSerializer(providers, many=True).data
        return JsonResponse({"providers": serialized_providers})
