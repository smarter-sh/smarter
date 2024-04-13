# pylint: disable=C0115
"""Django REST framework serializers for the API admin app."""
from rest_framework import serializers

from smarter.apps.chat.models import (
    ChatHistory,
    ChatToolCallHistory,
    PluginUsageHistory,
)


class ChatHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatHistory
        fields = "__all__"


class PluginUsageHistorySerializer(serializers.ModelSerializer):
    """Serializer for the PluginUsageHistory model."""

    class Meta:
        model = PluginUsageHistory
        fields = "__all__"


class ChatToolCallHistorySerializer(serializers.ModelSerializer):
    """Serializer for the ChatToolCallHistory model."""

    class Meta:
        model = ChatToolCallHistory
        fields = "__all__"
