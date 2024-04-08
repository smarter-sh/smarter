# -*- coding: utf-8 -*-
# pylint: disable=W0613,C0115
"""All models for the OpenAI Function Calling API app."""
from django.db import models
from django.forms.models import model_to_dict

from smarter.apps.chatbot.models import ChatBot
from smarter.apps.plugin.models import PluginMeta

# our stuff
from smarter.common.model_utils import TimestampedModel


# -----------------------------------------------------------------------------
# History Models.
# -----------------------------------------------------------------------------


class ChatHistory(TimestampedModel):
    """Chat history model."""

    chat_id = models.CharField(max_length=255, blank=True, null=True)
    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE, blank=True, null=True)
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
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


class ChatToolCallHistory(TimestampedModel):
    """Chat tool call history model."""

    EVENT_CHOICES = [
        ("called", "Called"),
        ("received", "Received"),
    ]

    plugin = models.ForeignKey(PluginMeta, on_delete=models.CASCADE, blank=True, null=True)
    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE, blank=True, null=True)
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    event = models.CharField(max_length=255, choices=EVENT_CHOICES, blank=True, null=True)
    model = models.CharField(max_length=255, blank=True, null=True)
    response = models.JSONField(blank=True, null=True)
    response_id = models.CharField(max_length=255, blank=True, null=True)

    def to_dict(self):
        """Return object as dictionary."""
        data = model_to_dict(self)
        data["plugin"] = model_to_dict(self.plugin) if self.plugin else None
        data["user"] = model_to_dict(self.user) if self.user else None
        return data

    def __str__(self):
        return f"{self.user} - {self.input_text[:50] if self.input_text else ''}"

    class Meta:
        verbose_name_plural = "Chat Tool Call History"


class PluginUsageHistory(TimestampedModel):
    """Plugin selection history model."""

    EVENT_CHOICES = [
        ("selected", "Selected"),
        ("called", "Called"),
    ]

    plugin = models.ForeignKey(PluginMeta, on_delete=models.CASCADE)
    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE, blank=True, null=True)
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    event = models.CharField(max_length=255, choices=EVENT_CHOICES, blank=True, null=True)
    data = models.JSONField(blank=True, null=True)
    model = models.CharField(max_length=255, blank=True, null=True)
    custom_tool = models.JSONField(max_length=255, blank=True, null=True)
    temperature = models.FloatField(blank=True, null=True)
    max_tokens = models.IntegerField(blank=True, null=True)
    custom_tool = models.JSONField(blank=True, null=True)
    inquiry_type = models.CharField(max_length=255, blank=True, null=True)
    inquiry_return = models.TextField(blank=True, null=True)

    def to_dict(self):
        """Return object as dictionary."""
        data = model_to_dict(self)
        data["plugin"] = self.plugin.to_dict() if self.plugin else None
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
        }
        return data

    def __str__(self):
        return f"{self.plugin} - {self.inquiry_type}"

    class Meta:
        verbose_name_plural = "Plugin Selection History"
