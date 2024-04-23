# pylint: disable=C0115
"""Django REST framework serializers for the API admin app."""
from rest_framework import serializers

from smarter.apps.chat.models import Chat, ChatHistory, ChatPluginUsage, ChatToolCall


class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = "__all__"


class ChatHistorySerializer(serializers.ModelSerializer):
    """Serializer for the ChatHistory model."""

    class Meta:
        model = ChatHistory
        fields = "__all__"


class ChatPluginUsageSerializer(serializers.ModelSerializer):
    """Serializer for the ChatPluginUsage model."""

    class Meta:
        model = ChatPluginUsage
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


class ChatToolCallSerializer(serializers.ModelSerializer):
    """Serializer for the ChatToolCall model."""

    class Meta:
        model = ChatToolCall
        fields = "__all__"
