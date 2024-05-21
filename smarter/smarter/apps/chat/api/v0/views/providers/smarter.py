# pylint: disable=R0801
"""Customer API views."""

from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
)


class SmarterChatApiViewSet(SmarterAuthenticatedAPIView):
    """top-level viewset for openai api function calling"""

    provider = "smarter"
