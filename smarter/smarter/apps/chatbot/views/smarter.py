# pylint: disable=W0611
"""
Smarter Customer API view.
"""
import json
import logging
from http import HTTPStatus

import waffle
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from smarter.apps.account.api.v0.serializers import AccountSerializer
from smarter.apps.chat.api.v0.serializers import (
    ChatHistorySerializer,
    ChatPluginUsageSerializer,
    ChatSerializer,
    ChatToolCallSerializer,
)
from smarter.apps.chat.models import (
    Chat,
    ChatHelper,
    ChatHistory,
    ChatPluginUsage,
    ChatToolCall,
)
from smarter.apps.chat.providers.smarter import handler
from smarter.apps.chatbot.api.v0.serializers import ChatBotSerializer
from smarter.lib.django.validators import SmarterValidator

from .base import ChatBotApiBaseViewSet


MAX_RETURNED_HISTORY = 25
CACHE_EXPIRATION = 60 * 30  # 5 minutes

logger = logging.getLogger(__name__)


class SmarterChatBotApiView(ChatBotApiBaseViewSet):
    """Main view for Smarter ChatBot API."""

    data: dict = {}
    chat_helper: ChatHelper = None
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
        self.session_key = self.data.get("session_key")
        SmarterValidator.validate_session_key(self.session_key)

        self.chat_helper = ChatHelper(session_key=self.session_key, request=request)
        self.chat = self.chat_helper.chat

        if waffle.switch_is_active("chatbot_api_view_logging"):
            logger.info("%s initialized with chat object %s", self.formatted_class_name, self.chat)

        return super().dispatch(request, *args, **kwargs)

    # pylint: disable=W0613
    def get(self, request, *args, **kwargs):
        if waffle.switch_is_active("chatbot_api_view_logging"):
            logger.info("%s.get() - %s", self.formatted_class_name, self.chat)

        chat = get_object_or_404(Chat, session_key=self.session_key)
        chat_history = ChatHistory.objects.filter(chat=chat).order_by("-pk")[:MAX_RETURNED_HISTORY]
        chat_tool_calls = ChatToolCall.objects.filter(chat=chat)
        chat_plugin_usage = ChatPluginUsage.objects.filter(chat=chat)

        data = {
            "session_key": self.session_key,
            "account": AccountSerializer(self.account).data if self.account else None,
            "chatbot": ChatBotSerializer(self.chatbot).data if self.chatbot else None,
            "chat": ChatSerializer(self.chat).data if self.chat else None,
            "history": (
                [ChatHistorySerializer(instance).data for instance in chat_history] if chat_history.exists() else None
            ),
            "tool_calls": (
                [ChatToolCallSerializer(instance).data for instance in chat_tool_calls]
                if chat_tool_calls.exists()
                else None
            ),
            "plugin_usage": (
                [ChatPluginUsageSerializer(instance).data for instance in chat_plugin_usage]
                if chat_plugin_usage.exists()
                else None
            ),
        }
        return JsonResponse(data=data, safe=False, status=HTTPStatus.OK)

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

        if waffle.switch_is_active("chatbot_api_view_logging"):
            logger.info("%s.post() - data=%s", self.formatted_class_name, self.data)
            logger.info("%s.post() - account: %s", self.formatted_class_name, self.account)
            logger.info("%s.post() - user: %s", self.formatted_class_name, self.user)
            logger.info("%s.post() - chat: %s", self.formatted_class_name, self.chat)
            logger.info("%s.post() - chatbot: %s", self.formatted_class_name, self.chatbot)
            logger.info("%s.post() - plugins: %s", self.formatted_class_name, self.plugins)

        response = handler(
            chat=self.chat,
            data=self.data,
            plugins=self.plugins,
            user=self.user,
            default_model=self.chatbot.default_model,
            default_temperature=self.chatbot.default_temperature,
            default_max_tokens=self.chatbot.default_max_tokens,
        )
        response = JsonResponse(data=response, safe=False, status=HTTPStatus.OK)
        if waffle.switch_is_active("chatbot_api_view_logging"):
            logger.info("%s response=%s", self.formatted_class_name, response)
        return response
