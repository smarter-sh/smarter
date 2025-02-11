# pylint: disable=W0611
"""
Smarter Customer API view.
"""

import logging
import traceback
from http import HTTPStatus

from django.http import JsonResponse

from smarter.apps.account.utils import get_cached_smarter_admin_user_profile

from .base import ChatBotApiBaseViewSet


logger = logging.getLogger(__name__)


class DefaultChatBotApiView(ChatBotApiBaseViewSet):
    """
    Main view for Smarter ChatBot API chat prompts.
    top-level viewset for customer-deployed Plugin-based Chat APIs.
    """

    def dispatch(self, request, *args, name: str = None, **kwargs):
        """
        Smarter API ChatBot dispatch method.

        Args:
            request: HttpRequest
            args: tuple
            name: str
            kwargs: dict

        request: {
            "session_key": "dde3dde5e3b97134f5bce5edf26ec05134da71d8485a86dfc9231149aaf0b0af",
            "messages": [
                {
                    "role": "assistant",
                    "content": "Welcome to Smarter!.  how can I assist you today?"
                },
                {
                    "role": "user",
                    "content": "Hello, World!"
                }
            ]
        }
        """
        self._name = name

        try:
            retval = super().dispatch(request, *args, **kwargs)
        # pylint: disable=broad-except
        except Exception as e:
            err_traceback = traceback.format_exc()
            logger.error("DefaultChatBotApiView.dispatch: %s, %s", e, err_traceback)
            retval = JsonResponse(
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                data={
                    "error": "An error occurred while processing your request.",
                    "details": str(e),
                    "trace": err_traceback,
                },
            )
        return retval
