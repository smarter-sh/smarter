# pylint: disable=missing-class-docstring
"""Chatbot serializers."""
from rest_framework import serializers

from smarter.apps.account.serializers import AccountMiniSerializer
from smarter.apps.plugin.serializers import PluginMetaSerializer

from .models import (
    ChatBot,
    ChatBotAPIKey,
    ChatBotCustomDomain,
    ChatBotFunctions,
    ChatBotPlugin,
)


class ChatBotSerializer(serializers.ModelSerializer):
    url_chatbot = serializers.ReadOnlyField()
    account = AccountMiniSerializer()

    class Meta:
        model = ChatBot
        fields = [
            "id",
            "account",
            "name",
            "description",
            "version",
            "subdomain",
            "custom_domain",
            "deployed",
            "default_model",
            "default_system_role",
            "default_temperature",
            "default_max_tokens",
            "app_name",
            "app_assistant",
            "app_welcome_message",
            "app_example_prompts",
            "app_placeholder",
            "app_info_url",
            "app_background_image_url",
            "app_logo_url",
            "app_file_attachment",
            "dns_verification_status",
            "url_chatbot",
        ]


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
