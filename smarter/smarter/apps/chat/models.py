# pylint: disable=W0613,C0115
"""All models for the OpenAI Function Calling API app."""
from django.db import models

from smarter.apps.plugin.models import PluginMeta

# our stuff
from smarter.lib.django.model_helpers import TimestampedModel


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


class PluginUsage(TimestampedModel):
    """Plugin selection history model."""

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    plugin = models.ForeignKey(PluginMeta, on_delete=models.CASCADE)
    input_text = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.chat.id} - {self.plugin.name}"

    class Meta:
        verbose_name_plural = "Plugin Selection Histories"
