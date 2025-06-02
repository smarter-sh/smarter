# pylint: disable=C0115
"""Django REST framework serializers for the API admin app."""
from rest_framework import serializers

from smarter.apps.plugin.serializers import PluginMetaSerializer
from smarter.apps.prompt.models import Chat, ChatHistory, ChatPluginUsage, ChatToolCall


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
