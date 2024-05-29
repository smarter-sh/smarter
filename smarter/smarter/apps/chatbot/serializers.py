# pylint: disable=missing-class-docstring
"""Chatbot serializers."""
from rest_framework import serializers

from smarter.apps.plugin.serializers import PluginMetaSerializer

from .models import (
    ChatBot,
    ChatBotAPIKey,
    ChatBotCustomDomain,
    ChatBotFunctions,
    ChatBotPlugin,
)


class ChatBotSerializer(serializers.ModelSerializer):

    class Meta:
        model = ChatBot
        fields = "__all__"


class ChatBotAPIKeySerializer(serializers.ModelSerializer):

    class Meta:
        model = ChatBotAPIKey
        fields = "__all__"


class ChatBotCustomDomainSerializer(serializers.ModelSerializer):

    class Meta:
        model = ChatBotCustomDomain
        fields = "__all__"


class ChatBotPluginSerializer(serializers.ModelSerializer):
    plugin_meta = PluginMetaSerializer()

    class Meta:
        model = ChatBotPlugin
        fields = "__all__"


class ChatBotFunctionsSerializer(serializers.ModelSerializer):

    class Meta:
        model = ChatBotFunctions
        fields = "__all__"
