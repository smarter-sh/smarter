# pylint: disable=C0115
"""Django REST framework serializers for the API admin app."""
from rest_framework import serializers

from smarter.apps.chat.models import Chat, ChatHistory, ChatPluginUsage, ChatToolCall
from smarter.apps.plugin.api.v0.serializers import PluginMetaSerializer


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


class ChatPluginUsageSerializer(serializers.ModelSerializer):
    """Serializer for the ChatPluginUsage model."""

    chat = ChatSerializer(read_only=True)
    plugin = PluginMetaSerializer()

    class Meta:
        model = ChatPluginUsage
        fields = "__all__"


class ChatToolCallSerializer(serializers.ModelSerializer):
    """Serializer for the ChatToolCall model."""

    chat = ChatSerializer(read_only=True)

    class Meta:
        model = ChatToolCall
        fields = "__all__"
