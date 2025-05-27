# pylint: disable=W0613,C0115
"""All models for the OpenAI Function Calling API app."""

import logging

from django.conf import settings
from django.core.cache import cache
from django.core.handlers.wsgi import WSGIRequest
from django.db import models
from django.db.utils import IntegrityError
from rest_framework import serializers

from smarter.apps.account.models import Account
from smarter.apps.chatbot.models import ChatBot, get_cached_chatbot_by_request
from smarter.apps.plugin.models import PluginMeta
from smarter.common.const import SmarterWaffleSwitches
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.django.request import SmarterRequestMixin


logger = logging.getLogger(__name__)


class Chat(TimestampedModel):
    """Chat model."""

    class Meta:
        verbose_name_plural = "Chats"
        unique_together = ("session_key", "url")

    session_key = models.CharField(max_length=255, blank=False, null=False, unique=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, blank=False, null=False)
    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE, blank=False, null=False)
    ip_address = models.GenericIPAddressField(blank=False, null=False)
    user_agent = models.CharField(max_length=255, blank=False, null=False)
    url = models.URLField(blank=False, null=False)

    def __str__(self):
        # pylint: disable=E1136
        return f"{self.id} - {self.ip_address} - {self.url}"

    def delete(self, *args, **kwargs):
        if self.session_key:
            cache.delete(self.session_key)
        super().delete(*args, **kwargs)


class ChatHistory(TimestampedModel):
    """Chat history model."""

    class Meta:
        verbose_name_plural = "Chat History"

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    request = models.JSONField(blank=True, null=True)
    response = models.JSONField(blank=True, null=True)
    messages = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.chat.id}"

    @property
    def chat_history(self) -> list[dict]:
        """
        Used by the Reactapp (via ChatConfigView) to display the chat history.
        """
        history = self.messages if self.messages else self.request.get("messages", []) if self.request else []
        # response = self.response.get("choices", []) if self.response else []
        # response = response[0] if response else {}
        # response = response.get("message", {})
        # history.append(response)
        return history


class ChatToolCall(TimestampedModel):
    """Chat tool call history model."""

    class Meta:
        verbose_name_plural = "Chat Tool Call History"

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    plugin = models.ForeignKey(PluginMeta, on_delete=models.CASCADE, blank=True, null=True)
    function_name = models.CharField(max_length=255, blank=True, null=True)
    function_args = models.CharField(max_length=255, blank=True, null=True)
    request = models.JSONField(blank=True, null=True)
    response = models.JSONField(blank=True, null=True)

    def __str__(self):
        if self.plugin:
            name = f"{self.chat.id} - {self.plugin.name}"
        else:
            name = f"{self.chat.id} - {self.function_name}"
        return name


class ChatPluginUsage(TimestampedModel):
    """Plugin selection history model."""

    class Meta:
        verbose_name_plural = "Plugin Usage"

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    plugin = models.ForeignKey(PluginMeta, on_delete=models.CASCADE)
    input_text = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.chat.id} - {self.plugin.name}"


# --------------------------------------------------------------------------------
# Serializers
# --------------------------------------------------------------------------------
class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = "__all__"


class ChatToolCallSerializer(serializers.ModelSerializer):
    """Serializer for the ChatToolCall model."""

    chat = ChatSerializer(read_only=True)

    class Meta:
        model = ChatToolCall
        fields = "__all__"


class ChatPluginUsageSerializer(serializers.ModelSerializer):
    """Serializer for the ChatPluginUsage model."""

    chat = ChatSerializer(read_only=True)

    class Meta:
        model = ChatPluginUsage
        fields = "__all__"


class ChatHelper(SmarterRequestMixin):
    """
    Helper class for working with Chat objects. Provides methods for
    creating and retrieving Chat objects and managing the cache.
    """

    _chat: Chat = None
    _chatbot: ChatBot = None
    _clean_url: str = None

    # FIX NOTE: remove session_key
    def __init__(self, request: WSGIRequest, session_key: str, *args, chatbot: ChatBot = None, **kwargs) -> None:
        if not request:
            logger.error("ChatHelper - request object is missing.")
        logger.info(
            "%s__init__() received session_key: %s, chatbot: %s", self.formatted_class_name, session_key, chatbot
        )
        SmarterRequestMixin.__init__(self, request=request, session_key=session_key, *args, **kwargs)
        self._chat: Chat = None
        self._chatbot: ChatBot = chatbot
        self._clean_url: str = None

        if not session_key and not chatbot:
            raise SmarterValueError(
                f"{self.formatted_class_name} either a session_key or a ChatBot instance is required"
            )

        if chatbot:
            self.account = chatbot.account

        if session_key:
            self._chat = self.get_cached_chat()

    def __str__(self):
        return self.session_key

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the formatted class name for the ChatBotHelper.
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.ChatHelper()"

    @property
    def chat(self):
        return self._chat

    @property
    def chatbot(self):
        if self._chatbot:
            return self._chatbot
        self._chatbot = get_cached_chatbot_by_request(request=self.request)

    @property
    def chat_history(self) -> ChatHistory:
        rec = ChatHistory.objects.filter(chat=self.chat).order_by("-created_at").first()
        return rec.chat_history if rec else []

    @property
    def chat_tool_call(self) -> models.QuerySet:
        recs = ChatToolCall.objects.filter(chat=self.chat).order_by("-created_at") or []
        return recs

    @property
    def chat_plugin_usage(self) -> models.QuerySet:
        recs = ChatPluginUsage.objects.filter(chat=self.chat).order_by("-created_at") or []
        return recs

    @property
    def history(self) -> dict:
        """
        Get the most recent logged history output for the chat session.
        """
        chat_serializer = ChatSerializer(self.chat)
        chat_tool_call_serializer = ChatToolCallSerializer(self.chat_tool_call, many=True)
        chat_plugin_usage_serializer = ChatPluginUsageSerializer(self.chat_plugin_usage, many=True)
        return {
            "chat": chat_serializer.data,
            "chat_history": self.chat_history,
            "chat_tool_call_history": chat_tool_call_serializer.data,
            "chat_plugin_usage_history": chat_plugin_usage_serializer.data,
            # these two will be added upstream.
            "chatbot_request_history": None,  # ChatBotRequests
        }

    @property
    def unique_client_string(self):
        if not self.account:
            return f"{self.url}{self.user_agent}{self.ip_address}"
        return f"{self.account.account_number}{self.url}{self.user_agent}{self.ip_address}"

    def get_cached_chat(self) -> Chat:
        """
        Get the chat instance for the current request.
        """
        if not self.smarter_request:
            logger.error("%s - request object is required for ChatHelper.", self.formatted_class_name)
            return None

        chat: Chat = cache.get(self.session_key)
        if chat:
            if waffle.switch_is_active(SmarterWaffleSwitches.CHAT_LOGGING) or waffle.switch_is_active(
                SmarterWaffleSwitches.CACHE_LOGGING
            ):
                logger.info(
                    "%s - retrieved cached Chat: %s session_key: %s", self.formatted_class_name, chat, chat.session_key
                )
            return chat

        if self.session_key:
            try:
                chat = Chat.objects.get(session_key=self.session_key)
                if waffle.switch_is_active(SmarterWaffleSwitches.CHAT_LOGGING):
                    logger.info(
                        "%s - retrieved Chat instance: %s session_key: %s",
                        self.formatted_class_name,
                        chat,
                        chat.session_key,
                    )
            except Chat.DoesNotExist:
                pass

        if not chat:
            if not self.chatbot:
                raise SmarterValueError(
                    f"{self.formatted_class_name} ChatBot instance is required for creating a Chat object."
                )

            try:
                # modify the unit test server URL
                # to a more Django friendly URL.
                django_friendly_url = self.url or ""
                django_friendly_url = django_friendly_url.replace("http://testserver/", "http://testserver.local/")
                chat = Chat.objects.create(
                    session_key=self.session_key,
                    account=self.account,
                    chatbot=self.chatbot,
                    ip_address=self.ip_address,
                    user_agent=self.user_agent,
                    url=django_friendly_url,
                )
            except IntegrityError as e:
                raise SmarterConfigurationError(f"{self.formatted_class_name} - IntegrityError: {str(e)}") from e

            if waffle.switch_is_active(SmarterWaffleSwitches.CHAT_LOGGING):
                logger.info(
                    "%s - created new Chat instance: %s session_key: %s",
                    self.formatted_class_name,
                    chat,
                    chat.session_key,
                )

        cache.set(key=self.session_key, value=chat, timeout=settings.SMARTER_CHAT_CACHE_EXPIRATION or 300)
        if waffle.switch_is_active(SmarterWaffleSwitches.CHAT_LOGGING) or waffle.switch_is_active(
            SmarterWaffleSwitches.CACHE_LOGGING
        ):
            logger.info(
                "%s - cached chat instance: %s session_key: %s", self.formatted_class_name, chat, chat.session_key
            )

        if not chat.chatbot:
            raise ValueError(f"{self.formatted_class_name} ChatBot instance is required for Chat object.")

        return chat
