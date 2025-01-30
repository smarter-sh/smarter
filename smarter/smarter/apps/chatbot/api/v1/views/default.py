# pylint: disable=W0611
"""
Smarter Customer API view.
"""
import logging
from http import HTTPStatus

import waffle

from smarter.apps.account.utils import smarter_admin_user_profile
from smarter.apps.chat.models import ChatHelper
from smarter.apps.chat.providers.providers import chat_providers
from smarter.apps.chatbot.exceptions import SmarterChatBotException
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME, SmarterWaffleSwitches
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.journal.enum import (
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
    SmarterJournalThings,
)
from smarter.lib.journal.http import (
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
)

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
            self.account = smarter_admin_user_profile().account
        retval = super().dispatch(request, *args, **kwargs)

        # Initialize the chat session for this request. session_key is generated
        # and managed by the /config/ endpoint for the chatbot
        #
        # example: https://customer-support.3141-5926-5359.api.smarter.sh/chatbot/config/
        #
        # The React app calls this endpoint at app initialization to get a
        # json dict that includes, among other pertinent info, this session_key
        # which uniquely identifies the device and the individual chatbot session
        # for the device.
        self._session_key = self.data.get(SMARTER_CHAT_SESSION_KEY_NAME)
        if self.session_key:
            SmarterValidator.validate_session_key(self.session_key)
        if self.chatbot or self.session_key:
            self.chat_helper = ChatHelper(request=request, session_key=self.session_key, chatbot=self.chatbot)
            self.helper_logger(
                (
                    "%s initialized with chat: %s, chatbot: %s",
                    self.formatted_class_name,
                    self.chat_helper.chat,
                    self.chatbot,
                )
            )

        return retval

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

        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
            logger.info(
                "%s.post() - provider=%s", self.formatted_class_name, self.chatbot.provider if self.chatbot else None
            )
            logger.info("%s.post() - data=%s", self.formatted_class_name, self.data)
            logger.info("%s.post() - account: %s", self.formatted_class_name, self.account)
            logger.info("%s.post() - user: %s", self.formatted_class_name, self.user)
            logger.info(
                "%s.post() - chat: %s", self.formatted_class_name, self.chat_helper.chat if self.chat_helper else None
            )
            logger.info("%s.post() - chatbot: %s", self.formatted_class_name, self.chatbot)
            logger.info("%s.post() - plugins: %s", self.formatted_class_name, self.plugins)

        if not self.chatbot:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=SmarterChatBotException("ChatBot not found"),
                safe=False,
                thing=SmarterJournalThings(SmarterJournalThings.CHATBOT),
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
                status=HTTPStatus.NOT_FOUND,
            )
        handler = chat_providers.get_handler(provider=self.chatbot.provider)
        if not self.chat_helper:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                e=SmarterChatBotException("ChatHelper not found"),
                safe=False,
                thing=SmarterJournalThings(SmarterJournalThings.CHATBOT),
                command=SmarterJournalCliCommands(SmarterJournalCliCommands.CHAT),
                status=HTTPStatus.NOT_FOUND,
            )
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
        self.helper_logger(("%s response=%s", self.formatted_class_name, response))
        return response

    def helper_logger(self, message: str):
        """
        Create a log entry
        """
        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING):
            logger.info(f"{self.formatted_class_name}: {message}")
