# pylint: disable=missing-class-docstring
"""Chatbot serializers."""
from rest_framework import serializers

from smarter.apps.account.serializers import AccountMiniSerializer
from smarter.apps.plugin.serializers import PluginMetaSerializer
from smarter.lib.drf.serializers import SmarterCamelCaseSerializer

from .models import (
    ChatBot,
    ChatBotAPIKey,
    ChatBotCustomDomain,
    ChatBotFunctions,
    ChatBotPlugin,
)


class ChatBotSerializer(SmarterCamelCaseSerializer):
    url_chatbot = serializers.ReadOnlyField()
    account = AccountMiniSerializer()
    default_system_role = serializers.SerializerMethodField()

    class Meta:
        model = ChatBot
        fields = "__all__"

    def get_default_system_role(self, obj: ChatBot):
        return obj.default_system_role_enhanced


class ChatBotAPIKeySerializer(SmarterCamelCaseSerializer):

    class Meta:
        model = ChatBotAPIKey
        fields = "__all__"


class ChatBotCustomDomainSerializer(SmarterCamelCaseSerializer):

    class Meta:
        model = ChatBotCustomDomain
        fields = "__all__"


class ChatBotPluginSerializer(SmarterCamelCaseSerializer):
    plugin_meta = PluginMetaSerializer()

    class Meta:
        model = ChatBotPlugin
        fields = "__all__"


class ChatBotFunctionsSerializer(SmarterCamelCaseSerializer):

    class Meta:
        model = ChatBotFunctions
        fields = "__all__"
