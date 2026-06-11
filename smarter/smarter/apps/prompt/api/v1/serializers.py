# pylint: disable=C0115
"""Django REST framework serializers for the API admin app."""

from rest_framework import serializers

from smarter.apps.plugin.serializers import PluginMetaSerializer
from smarter.apps.prompt.models import (
    Chat,
    PromptHistory,
    PromptPluginUsage,
    PromptToolCall,
)


class PromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = "__all__"


class ChatHistorySerializer(serializers.ModelSerializer):
    """Serializer for the PromptHistory model."""

    chat = PromptSerializer(read_only=True)

    class Meta:
        model = PromptHistory
        fields = "__all__"


class PromptPluginUsageSerializer(serializers.ModelSerializer):
    """Serializer for the PromptPluginUsage model."""

    chat = PromptSerializer(read_only=True)
    plugin = PluginMetaSerializer()

    class Meta:
        model = PromptPluginUsage
        fields = "__all__"


class PromptToolCallSerializer(serializers.ModelSerializer):
    """Serializer for the PromptToolCall model."""

    chat = PromptSerializer(read_only=True)

    class Meta:
        model = PromptToolCall
        fields = "__all__"
