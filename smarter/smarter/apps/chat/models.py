# pylint: disable=W0613,C0115
"""All models for the OpenAI Function Calling API app."""

import logging

import waffle
from django.conf import settings
from django.core.cache import cache
from django.db import models

from smarter.apps.plugin.models import PluginMeta
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.django.request import SmarterRequestHelper


logger = logging.getLogger(__name__)
# -----------------------------------------------------------------------------
# History Models.
# -----------------------------------------------------------------------------


class Chat(TimestampedModel):
    """Chat model."""

    session_key = models.CharField(max_length=255, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    url = models.URLField(blank=True, null=True)

    def __str__(self):
        # pylint: disable=E1136
        return f"{self.ip_address} - {self.url}"

    class Meta:
        verbose_name_plural = "Chats"


class ChatHistory(TimestampedModel):
    """Chat history model."""

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    request = models.JSONField(blank=True, null=True)
    response = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.chat.id}"

    class Meta:
        verbose_name_plural = "Chat Histories"


class ChatToolCall(TimestampedModel):
    """Chat tool call history model."""

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

    class Meta:
        verbose_name_plural = "Chat Tool Call Histories"


class ChatPluginUsage(TimestampedModel):
    """Plugin selection history model."""

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    plugin = models.ForeignKey(PluginMeta, on_delete=models.CASCADE)
    input_text = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.chat.id} - {self.plugin.name}"

    class Meta:
        verbose_name_plural = "Plugin Usage"


class ChatHelper(SmarterRequestHelper):
    """
    Helper class for working with Chat objects. Provides methods for
    creating and retrieving Chat objects and managing the cache.
    """

    _session_key: str = None
    _chat: Chat = None

    def __init__(self, session_key: str, request) -> None:
        super().__init__(request)
        self._session_key = session_key
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
    def formatted_class_name(self):
        return formatted_text(self.__class__.__name__)

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
                chat.save()
            cache.set(key=self.session_key, value=chat, timeout=settings.SMARTER_CHAT_CACHE_EXPIRATION)
            if waffle.switch_is_active("chat_logging"):
                logger.info("%s - cached chat object %s", self.formatted_class_name, chat)

        return chat
