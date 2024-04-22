# pylint: disable=C0115
"""Django REST framework serializers for the API admin app."""
from rest_framework import serializers

from smarter.apps.chat.models import Chat, ChatToolCall, PluginUsage


class ChatHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = "__all__"


class PluginUsageHistorySerializer(serializers.ModelSerializer):
    """Serializer for the PluginUsage model."""

    class Meta:
        model = PluginUsage
        fields = [
            "user",
            "event",
            "data",
            "model",
            "custom_tool",
            "temperature",
            "max_tokens",
            "custom_tool",
            "inquiry_type",
            "inquiry_return",
        ]


class ChatToolCallHistorySerializer(serializers.ModelSerializer):
    """Serializer for the ChatToolCall model."""

    class Meta:
        model = ChatToolCall
        fields = "__all__"
