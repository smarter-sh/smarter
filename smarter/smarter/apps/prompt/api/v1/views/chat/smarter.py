# pylint: disable=R0801
"""Customer API views."""

from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
)


class SmarterChatApiViewSet(SmarterAuthenticatedAPIView):
    """top-level viewset for openai api function calling"""

    provider_name: str

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.provider_name = self.kwargs.pop("provider_name")
