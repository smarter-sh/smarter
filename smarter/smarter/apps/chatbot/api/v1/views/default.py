# pylint: disable=W0611
"""
Smarter Customer API view.
"""
import logging
from http import HTTPStatus

import waffle

from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.apps.chat.models import ChatHelper

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

        # FIX NOTE: this is kludgy, but it works for now.
        # handles the case of smarter example chatbots
        # like /smarter/example/
        account_name = kwargs.get("account")
        if account_name == "smarter":
            self.account = get_cached_smarter_admin_user_profile().account
        retval = super().dispatch(request, *args, **kwargs)

        return retval
