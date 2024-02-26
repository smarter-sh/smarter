# -*- coding: utf-8 -*-
"""Django REST framework serializers for the API admin app."""
from rest_framework import serializers

from .models import ChatHistory, ChatToolCallHistory, PluginUsageHistory


class ChatHistorySerializer(serializers.HyperlinkedModelSerializer):
    """Serializer for the ChatHistory model."""

    class Meta:
        """Meta class for the ChatHistorySerializer."""

        model = ChatHistory
        fields = [
            "url",
            "user",
            "input_text",
            "model",
            "messages",
            "tools",
            "temperature",
            "max_tokens",
            "response",
            "response_id",
        ]


class PluginUsageHistorySerializer(serializers.HyperlinkedModelSerializer):
    """Serializer for the PluginUsageHistory model."""

    class Meta:
        """Meta class for the PluginUsageHistorySerializer."""

        model = PluginUsageHistory
        fields = ["url", "plugin", "user", "event", "input_text", "model", "messages", "response", "response_id"]


class ChatToolCallHistorySerializer(serializers.HyperlinkedModelSerializer):
    """Serializer for the ChatToolCallHistory model."""

    class Meta:
        """Meta class for the ChatToolCallHistorySerializer."""

        model = ChatToolCallHistory
        fields = ["url", "plugin", "user", "event", "input_text", "model", "messages", "response", "response_id"]
