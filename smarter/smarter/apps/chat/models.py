# pylint: disable=W0613,C0115
"""All models for the OpenAI Function Calling API app."""

import logging

import waffle
from django.conf import settings
from django.core.cache import cache
from django.db import models
from rest_framework import serializers

from smarter.apps.account.models import Account
from smarter.apps.chatbot.models import ChatBot
from smarter.apps.plugin.models import PluginMeta
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.django.request import SmarterRequestHelper


logger = logging.getLogger(__name__)
# -----------------------------------------------------------------------------
# History Models.
# -----------------------------------------------------------------------------


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
        return f"{self.ip_address} - {self.url}"

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

    def __str__(self):
        return f"{self.chat.id}"

    @property
    def chat_history(self) -> list[dict]:
        history = self.request.get("messages", [])
        response = self.response.get("choices", [])
        response = response[0] if response else {}
        response = response.get("message", {})
        history.append(response)
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


class ChatHistorySerializer(serializers.ModelSerializer):
    """Serializer for the ChatHistory model."""

    chat = ChatSerializer(read_only=True)

    class Meta:
        model = ChatHistory
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

    def __init__(self, session_key: str, request, chatbot: ChatBot = None) -> None:
        super().__init__(request)
        self._session_key = session_key
        self._chatbot = chatbot
        self._chat = self.get_cached_chat()
        if waffle.switch_is_active("chat_logging"):
            logger.info("%s - initialized chat %s", self.formatted_class_name, self.chat)

    @property
    def chat(self):
        return self._chat

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
    def console(self) -> dict:
        """
        Get the most recent logged console output for the chat session.
        """
        chat_history_serializer = ChatHistorySerializer(self.chat_history, many=True)
        chat_tool_call_serializer = ChatToolCallSerializer(self.chat_tool_call, many=True)
        chat_plugin_usage_serializer = ChatPluginUsageSerializer(self.chat_plugin_usage, many=True)
        return {
            SMARTER_CHAT_SESSION_KEY_NAME: self.session_key,
            "chat": self.chat.id,
            "chat_history": chat_history_serializer.data,
            "chat_tool_call": chat_tool_call_serializer.data,
            "chat_plugin_usage": chat_plugin_usage_serializer.data,
        }

    def get_cached_chat(self):
        """
        Get the chat instance for the current request.
        """
        chat = cache.get(self.session_key)
        if chat:
            if waffle.switch_is_active("chat_logging"):
                logger.info("%s - retrieved cached chat %s", self.formatted_class_name, chat)
        else:
            chat, created = Chat.objects.get_or_create(session_key=self.session_key)
            if created:
                chat.url = self.url
                chat.ip_address = self.ip_address
                chat.user_agent = self.user_agent
                chat.chatbot = self.chatbot
                chat.save()
            if not chat.chatbot:
                raise ValueError("ChatBot instance is required for Chat object.")

            cache.set(key=self.session_key, value=chat, timeout=settings.SMARTER_CHAT_CACHE_EXPIRATION or 300)
            if waffle.switch_is_active("chat_logging"):
                logger.info("%s - cached chat object %s", self.formatted_class_name, chat)

        return chat
