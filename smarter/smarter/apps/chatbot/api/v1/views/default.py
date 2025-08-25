# pylint: disable=W0611
"""
Smarter Customer API view.
"""

import logging
import traceback
from http import HTTPStatus
from typing import Optional

from django.http import JsonResponse

from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .base import ChatBotApiBaseViewSet


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class DefaultChatbotApiView(ChatBotApiBaseViewSet):
    """
    Main view for Smarter ChatBot API chat prompts.
    top-level viewset for customer-deployed Plugin-based Chat APIs.
    """

    def dispatch(self, request, *args, name: Optional[str] = None, **kwargs):
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
        logger.info("%s - dispatch()", self.formatted_class_name)
        self._name = name

        try:
            retval = super().dispatch(request, *args, **kwargs)
        # pylint: disable=broad-except
        except Exception as e:
            err_traceback = traceback.format_exc()
            logger.error("DefaultChatbotApiView.dispatch: %s, %s", e, err_traceback)
            retval = JsonResponse(
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                data={
                    "error": "An error occurred while processing your request.",
                    "details": str(e),
                    "trace": err_traceback,
                },
            )
        return retval
