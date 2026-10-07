# pylint: disable=R0801
"""Customer API views."""

from rest_framework.request import Request

from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
)


class SmarterChatApiViewSet(SmarterAuthenticatedAPIView):
    """
    Top-level viewset for openai api function calling.

    path: /api/v1/prompt/prompt/smarter/{provider_name}/
    """

    provider_name: str

    def setup(self, request: Request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.provider_name = self.kwargs.pop("provider_name")
