# -*- coding: utf-8 -*-
# pylint: disable=W0613,C0115
"""All models for the OpenAI Function Calling API app."""
from django.db import models

from smarter.apps.chat.signals import (
    chat_completion_history_created,
    chat_completion_tool_call_history_created,
    plugin_selection_history_created,
)

# our stuff
from smarter.apps.common.model_utils import TimestampedModel
from smarter.apps.plugin.models import PluginMeta


# Create your models here.
class ChatHistory(TimestampedModel):
    """Chat history model."""

    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    input_text = models.TextField(blank=True, null=True)
    model = models.CharField(max_length=255, blank=True, null=True)
    messages = models.JSONField(blank=True, null=True)
    tools = models.JSONField(max_length=255, blank=True, null=True)
    temperature = models.FloatField(blank=True, null=True)
    max_tokens = models.IntegerField(blank=True, null=True)
    response = models.JSONField(blank=True, null=True)
    response_id = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        chat_completion_history_created.send(sender=ChatHistory, user=self.user, data=self)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.user_prompt}"

    class Meta:
        verbose_name_plural = "Chat History"


class ChatToolCallHistory(TimestampedModel):
    """Chat tool call history model."""

    EVENT_CHOICES = [
        ("called", "Called"),
        ("received", "Received"),
    ]

    plugin = models.ForeignKey(PluginMeta, on_delete=models.CASCADE)
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    event = models.CharField(max_length=255, choices=EVENT_CHOICES, blank=True, null=True)
    input_text = models.TextField(blank=True, null=True)
    model = models.CharField(max_length=255, blank=True, null=True)
    messages = models.JSONField(blank=True, null=True)
    response = models.JSONField(blank=True, null=True)
    response_id = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        chat_completion_tool_call_history_created.send(sender=ChatToolCallHistory, user=self.user, data=self)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.user_prompt}"

    class Meta:
        verbose_name_plural = "Chat Tool Call History"


class PluginUsageHistory(TimestampedModel):
    """Plugin selection history model."""

    EVENT_CHOICES = [
        ("selected", "Selected"),
        ("called", "Called"),
    ]

    plugin = models.ForeignKey(PluginMeta, on_delete=models.CASCADE)
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    event = models.CharField(max_length=255, choices=EVENT_CHOICES, blank=True, null=True)
    data = models.JSONField(blank=True, null=True)
    model = models.CharField(max_length=255, blank=True, null=True)
    messages = models.JSONField(blank=True, null=True)
    custom_tool = models.JSONField(max_length=255, blank=True, null=True)
    temperature = models.FloatField(blank=True, null=True)
    max_tokens = models.IntegerField(blank=True, null=True)
    custom_tool = models.JSONField(blank=True, null=True)
    input_text = models.TextField(blank=True, null=True)
    inquiry_type = models.CharField(max_length=255, blank=True, null=True)
    inquiry_return = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        plugin_selection_history_created.send(sender=PluginUsageHistory, user=self.user, data=self)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.plugin} - {self.inquiry_type}"

    class Meta:
        verbose_name_plural = "Plugin Selection History"
