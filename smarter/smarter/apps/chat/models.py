# pylint: disable=W0613,C0115
"""All models for the OpenAI Function Calling API app."""

import logging
import urllib.parse

import waffle
from django.conf import settings
from django.core.cache import cache
from django.db import models
from rest_framework import serializers

from smarter.apps.account.models import Account
from smarter.apps.chatbot.models import ChatBot
from smarter.apps.plugin.models import PluginMeta
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME, SmarterWaffleSwitches
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.django.request import SmarterRequestHelper


logger = logging.getLogger(__name__)


class Chat(TimestampedModel):
    """Chat model."""

    class Meta:
        verbose_name_plural = "Chats"
        unique_together = (SMARTER_CHAT_SESSION_KEY_NAME, "url")

    session_key = models.CharField(max_length=255, blank=True, null=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, blank=True, null=True)
    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    url = models.URLField(blank=True, null=True)

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


class ChatHelper(SmarterRequestHelper):
    """
    Helper class for working with Chat objects. Provides methods for
    creating and retrieving Chat objects and managing the cache.
    """

    _session_key: str = None
    _chat: Chat = None
    _chatbot: ChatBot = None
    _clean_url: str = None

    def __init__(self, session_key: str, request, chatbot: ChatBot = None) -> None:
        super().__init__(request)
        self._session_key = session_key
        self._chatbot = chatbot
        self._chat = self.get_cached_chat()
        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHAT_LOGGING):
            logger.info(
                "%s - initialized chat: %s session_key: %s", self.formatted_class_name, self.chat, self.chat.session_key
            )

    @property
    def chat(self):
        return self._chat

    @property
    def url(self) -> str:
        if self._clean_url:
            return self._clean_url

        super_url = super().url
        if super_url is None:
            return None
        parsed_url = urllib.parse.urlparse(super_url)
        self._clean_url = parsed_url._replace(query="").geturl()
        if self._clean_url.endswith("/config/"):
            self._clean_url = self._clean_url[:-8]

        return self._clean_url

    @property
    def session_key(self):
        return self._session_key

    @property
    def chatbot(self):
        return self._chatbot

    @property
    def formatted_class_name(self):
        return formatted_text(self.__class__.__name__)

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

    def get_cached_chat(self) -> Chat:
        """
        Get the chat instance for the current request.
        """
        chat = cache.get(self.session_key)

        if isinstance(chat, dict):
            chat = Chat(**chat)

        if chat:
            if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHAT_LOGGING):
                logger.info(
                    "%s - retrieved cached chat: %s session_key: %s", self.formatted_class_name, chat, chat.session_key
                )
            return chat

        chat, created = Chat.objects.get_or_create(session_key=self.session_key)
        if created:
            chat.url = self.url
            chat.ip_address = self.ip_address
            chat.user_agent = self.user_agent
            chat.chatbot = self.chatbot
            chat.save()
        else:
            if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHAT_LOGGING):
                logger.info(
                    "%s - queried chat instance: %s session_key: %s", self.formatted_class_name, chat, chat.session_key
                )

        cache.set(key=self.session_key, value=chat, timeout=settings.SMARTER_CHAT_CACHE_EXPIRATION or 300)
        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_CHAT_LOGGING):
            logger.info(
                "%s - cached chat instance: %s session_key: %s", self.formatted_class_name, chat, chat.session_key
            )

        if not chat.chatbot:
            raise ValueError(f"{self.formatted_class_name} ChatBot instance is required for Chat object.")

        return chat
