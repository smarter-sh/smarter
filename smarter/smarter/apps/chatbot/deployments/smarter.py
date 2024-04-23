# pylint: disable=W0611
"""
Smarter Customer API view.
"""
import json
import logging
from http import HTTPStatus

from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from smarter.apps.chat.models import Chat
from smarter.apps.chat.providers.smarter import handler

from .base import ChatBotApiBaseViewSet


logger = logging.getLogger(__name__)


class SmarterChatBotApiViewSet(ChatBotApiBaseViewSet):
    """Main view for Smarter ChatBot API."""

    data: dict = {}
    chat: Chat = None
    session_key: str = None

    """
    top-level viewset for customer-deployed Plugin-based Chat APIs.
    """

    def dispatch(self, request, *args, **kwargs):
        kwargs.pop("chatbot_id", None)
        try:
            self.data = json.loads(request.body)
        except json.JSONDecodeError:
            self.data = {}

        # Initialize the chat session for this request. session_key is generated
        # and managed by the /config/ endpoint for the chatbot
        #
        # example: https://customer-support.3141-5926-5359.api.smarter.sh/chatbot/config/
        #
        # The React app calls this endpoint at app initialization to get a
        # json dict that includes, among other pertinent info, this session_key
        # which uniquely identifies the device and the individual chatbot session
        # for the device.
        self.session_key = self.data.get("session_key")
        self.chat = get_object_or_404(Chat, session_key=self.session_key)

    # pylint: disable=W0613
    def post(self, request, *args, **kwargs):
        """
        POST request handler for the Smarter Chat API. We need to parse the request host
        to determine which ChatBot instance to use. There are two possible hostname formats:

        URL with default api domain
        -------------------
        example: https://customer-support.3141-5926-5359.api.smarter.sh/chatbot/
        where
         - `customer-service' == chatbot.name`
         - `3141-5926-5359 == chatbot.account.account_number`
         - `api.smarter.sh == smarter_settings.customer_api_domain`

        URL with custom domain
        -------------------
        example: https://api.smarter.querium.com/chatbot/
        where
         - `api.smarter.querium.com == chatbot.custom_domain`
         - `ChatBotCustomDomain.is_verified == True` noting that
           an asynchronous task has verified the domain NS records.

        The ChatBot instance hostname is determined by the following logic:
        `chatbot.hostname == chatbot.custom_domain or chatbot.default_host`
        """

        logger.debug("SmarterChatBotApiViewSet.post: data=%s", self.data)
        logger.debug("account: %s", self.account)
        logger.debug("user: %s", self.user)
        logger.debug("chatbot: %s", self.chatbot)
        logger.debug("plugins: %s", self.plugins)

        response = handler(
            chat_id=self.chat.id,
            data=self.data,
            plugins=self.plugins,
            user=self.user,
            default_model=self.chatbot.default_model,
            default_temperature=self.chatbot.default_temperature,
            default_max_tokens=self.chatbot.default_max_tokens,
        )
        response = JsonResponse(data=response, safe=False, status=HTTPStatus.OK)
        logger.debug("SmarterChatBotApiViewSet.post: response=%s", response)
        return response
