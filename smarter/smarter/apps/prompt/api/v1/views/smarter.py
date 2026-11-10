# pylint: disable=R0801
"""Customer API views."""

from django.http import HttpRequest

from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
)


class SmarterChatApiViewSet(SmarterAuthenticatedAPIView):
    """
    Top-level viewset for openai api function calling.

    path: /api/v1/prompt/prompt/smarter/{provider_name}/
    """

    provider_name: str

    def setup(self, request: HttpRequest, *args, **kwargs):
        """
        Set up the view, and move the url's ``provider_name`` from ``self.kwargs`` to ``self.provider_name``.

        :param request: The request.
        :param args: Positional arguments passed to the parent's ``setup()``.
        :param kwargs: The url's keyword arguments, including ``provider_name``.
        """
        super().setup(request, *args, **kwargs)
        self.provider_name = self.kwargs.pop("provider_name")
