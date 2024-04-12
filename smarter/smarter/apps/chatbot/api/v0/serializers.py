# -*- coding: utf-8 -*-
# pylint: disable=C0114,C0115,C0116
"""Account serializers for smarter api"""
from rest_framework import serializers

from smarter.apps.account.api.v0.serializers import AccountSerializer, APIKeySerializer
from smarter.apps.chatbot.models import (
    ChatBot,
    ChatBotAPIKey,
    ChatBotCustomDomain,
    ChatBotCustomDomainDNS,
    ChatBotFunctions,
    ChatBotPlugin,
)
from smarter.apps.plugin.api.v0.serializers import PluginMetaSerializer


class ChatBotSerializer(serializers.ModelSerializer):

    class Meta:
        model = ChatBot
        fields = "__all__"


class ChatBotAPIKeySerializer(serializers.ModelSerializer):

    chatbot = ChatBotSerializer()
    api_key = APIKeySerializer()

    class Meta:
        model = ChatBotAPIKey
        fields = "__all__"


class ChatBotCustomDomainSerializer(serializers.ModelSerializer):

    account = AccountSerializer()

    class Meta:
        model = ChatBotCustomDomain
        fields = "__all__"


class ChatBotCustomDomainDNSSerializer(serializers.ModelSerializer):

    custom_domain = ChatBotCustomDomainSerializer()

    class Meta:
        model = ChatBotCustomDomainDNS
        fields = "__all__"


class ChatBotFunctionsSerializer(serializers.ModelSerializer):

    chatbot = ChatBotSerializer()

    class Meta:
        model = ChatBotFunctions
        fields = "__all__"


class ChatBotPluginSerializer(serializers.ModelSerializer):

    chatbot = ChatBotSerializer()
    plugin_meta = PluginMetaSerializer()

    class Meta:
        model = ChatBotPlugin
        fields = "__all__"
