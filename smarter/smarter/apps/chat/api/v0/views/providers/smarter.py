# -*- coding: utf-8 -*-
# pylint: disable=R0801
"""Customer API views."""

from smarter.apps.account.api.view_helpers import SmarterAPIView


class SmarterChatViewSet(SmarterAPIView):
    """top-level viewset for openai api function calling"""

    provider = "smarter"
