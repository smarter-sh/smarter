# pylint: disable=W0611
"""
Smarter Customer API view.
"""
import json
import logging
from http import HTTPStatus

import waffle

from smarter.apps.chat.models import ChatHelper
from smarter.apps.chat.providers.providers import ChatProviders
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.journal.enum import (
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
    SmarterJournalThings,
)
from smarter.lib.journal.http import SmarterJournaledJsonResponse

from .base import ChatBotApiBaseViewSet


chat_providers = ChatProviders()
logger = logging.getLogger(__name__)


class DefaultChatBotApiView(ChatBotApiBaseViewSet):
    """Main view for Smarter ChatBot API."""

    data: dict = {}
    chat_helper: ChatHelper = None

    """
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
        logger.info("DefaultChatBotApiView.dispatch() - name=%s", name)
        kwargs.pop("chatbot_id", None)
        self.request = request
        self._user = request.user
        self._name = name
        try:
            self.data = json.loads(request.body)
        except json.JSONDecodeError:
            self.data = {}
        if waffle.switch_is_active("chatbot_api_view_logging"):
            logger.info("%s - data=%s", self.formatted_class_name, self.data)

        # Initialize the chat session for this request. session_key is generated
        # and managed by the /config/ endpoint for the chatbot
        #
        # example: https://customer-support.3141-5926-5359.api.smarter.sh/chatbot/config/
        #
        # The React app calls this endpoint at app initialization to get a
        # json dict that includes, among other pertinent info, this session_key
        # which uniquely identifies the device and the individual chatbot session
        # for the device.
        self._session_key = self.data.get("session_key")
        if self.session_key:
            SmarterValidator.validate_session_key(self.session_key)
        self.chat_helper = ChatHelper(session_key=self.session_key, request=request, chatbot=self.chatbot)

        if waffle.switch_is_active("chatbot_api_view_logging"):
            logger.info("%s initialized with chat object %s", self.formatted_class_name, self.chat_helper.chat)

        return super().dispatch(request, *args, **kwargs)

    # pylint: disable=W0613
    def post(self, request, *args, name: str = None, **kwargs):
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

        if waffle.switch_is_active("chatbot_api_view_logging"):
            logger.info("%s.post() - data=%s", self.formatted_class_name, self.data)
            logger.info("%s.post() - account: %s", self.formatted_class_name, self.account)
            logger.info("%s.post() - user: %s", self.formatted_class_name, self.user)
            logger.info("%s.post() - chat: %s", self.formatted_class_name, self.chat_helper.chat)
            logger.info("%s.post() - chatbot: %s", self.formatted_class_name, self.chatbot)
            logger.info("%s.post() - plugins: %s", self.formatted_class_name, self.plugins)

        handler = chat_providers.get_handler(name=self.chatbot.provider)
        response = handler(chat=self.chat_helper.chat, data=self.data, plugins=self.plugins, user=self.user)
        response = {
            SmarterJournalApiResponseKeys.DATA: response,
        }
        response = SmarterJournaledJsonResponse(
            request=request,
            data=response,
            command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
            thing=SmarterJournalThings(SmarterJournalThings.CHATBOT),
            status=HTTPStatus.OK,
            safe=False,
        )
        if waffle.switch_is_active("chatbot_api_view_logging"):
            logger.info("%s response=%s", self.formatted_class_name, response)
        return response
