# pylint: disable=W0613,C0115
"""All models for the OpenAI Function Calling API app."""
from django.db import models
from django.forms.models import model_to_dict

from smarter.apps.plugin.models import PluginMeta

# our stuff
from smarter.lib.django.model_helpers import TimestampedModel


# -----------------------------------------------------------------------------
# History Models.
# -----------------------------------------------------------------------------


class Chat(TimestampedModel):
    """Chat history model."""

    model = models.CharField(max_length=255, blank=True, null=True)
    tools = models.JSONField(max_length=255, blank=True, null=True)
    temperature = models.FloatField(blank=True, null=True)
    max_tokens = models.IntegerField(blank=True, null=True)
    messages = models.JSONField(blank=True, null=True)
    response = models.JSONField(blank=True, null=True)

    def to_dict(self):
        """Return object as dictionary."""
        data = model_to_dict(self)
        data["user"] = model_to_dict(self.user) if self.user else None
        return data

    def __str__(self):
        # pylint: disable=E1136
        return f"{self.user} - {self.chat_id[:50] if self.chat_id else ''}"

    class Meta:
        verbose_name_plural = "Chat History"


class ChatHistory(TimestampedModel):
    """Chat history model."""

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    request = models.JSONField(blank=True, null=True)
    response = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.chat.id}"

    class Meta:
        verbose_name_plural = "Chat History"


class ChatToolCall(TimestampedModel):
    """Chat tool call history model."""

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    plugin = models.ForeignKey(PluginMeta, on_delete=models.CASCADE, blank=True, null=True)
    tool_call = models.JSONField(blank=True, null=True)
    request = models.JSONField(blank=True, null=True)
    response = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.chat.id}"

    class Meta:
        verbose_name_plural = "Chat Tool Call History"


class PluginUsage(TimestampedModel):
    """Plugin selection history model."""

    EVENT_CHOICES = [
        ("selected", "Selected"),
        ("called", "Called"),
    ]

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    plugin = models.ForeignKey(PluginMeta, on_delete=models.CASCADE)
    input_text = models.TextField(blank=True, null=True)
    inquiry_type = models.CharField(max_length=255, blank=True, null=True)
    inquiry_return = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.plugin.name}"

    class Meta:
        verbose_name_plural = "Plugin Selection History"
