# pylint: disable=missing-class-docstring,W0212
"""Chatbot serializers."""

from rest_framework import serializers

from smarter.apps.account.serializers import (
    MetaDataWithOwnershipModelSerializer,
    UserProfileSerializer,
)
from smarter.apps.plugin.serializers import PluginMetaSerializer
from smarter.lib.drf.serializers import SmarterCamelCaseSerializer

from .models import (
    ChatBot,
    ChatBotAPIKey,
    ChatBotCustomDomain,
    ChatBotFunctions,
    ChatBotPlugin,
    ChatBotRequests,
)


class ChatBotRequestsSerializer(serializers.ModelSerializer):
    """
    Serializer for the ChatBotRequests model.
    """

    # pylint: disable=C0115
    class Meta:
        model = ChatBotRequests
        fields = (
            "id",
            "created_at",
            "updated_at",
            "request",
            "is_aggregation",
        )


class ChatBotConfigSerializer(serializers.ModelSerializer):
    """
    Serializer for the smarter.apps.prompt.views.ChatConfigView
    which should not be camelCased.
    """

    url_chatbot = serializers.ReadOnlyField()
    user_profile = UserProfileSerializer()
    default_system_role = serializers.SerializerMethodField()
    annotations = serializers.JSONField()

    class Meta:
        model = ChatBot
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields

    def get_default_system_role(self, obj: ChatBot):
        return obj.default_system_role_enhanced


class ChatBotAPIKeySerializer(SmarterCamelCaseSerializer):

    class Meta:
        model = ChatBotAPIKey
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


class ChatBotCustomDomainSerializer(MetaDataWithOwnershipModelSerializer):

    class Meta:
        model = ChatBotCustomDomain
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


class ChatBotPluginSerializer(SmarterCamelCaseSerializer):
    plugin_meta = PluginMetaSerializer()

    class Meta:
        model = ChatBotPlugin
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


class ChatBotPluginMiniSerializer(SmarterCamelCaseSerializer):

    # pylint: disable=C0115
    class Meta:
        model = ChatBotPlugin
        fields = ("id", "name")

    name = serializers.CharField(source="plugin_meta.name", read_only=True)


class ChatBotFunctionsSerializer(SmarterCamelCaseSerializer):

    class Meta:
        model = ChatBotFunctions
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


class ChatBotSerializer(MetaDataWithOwnershipModelSerializer):
    hashed_id = serializers.SerializerMethodField()
    url_chatbot = serializers.ReadOnlyField()
    user_profile = UserProfileSerializer()
    functions = serializers.SerializerMethodField()
    plugins = serializers.SerializerMethodField()
    custom_domains = serializers.SerializerMethodField()
    api_keys = serializers.SerializerMethodField()
    rfc1034_compliant_name = serializers.SerializerMethodField()
    default_system_role = serializers.SerializerMethodField()
    base_api_domain = serializers.SerializerMethodField()
    base_default_host = serializers.SerializerMethodField()
    default_host = serializers.SerializerMethodField()
    default_url = serializers.SerializerMethodField()
    custom_host = serializers.SerializerMethodField()
    custom_url = serializers.SerializerMethodField()
    sandbox_host = serializers.SerializerMethodField()
    sandbox_url = serializers.SerializerMethodField()
    hostname = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    url_chatbot = serializers.SerializerMethodField()
    url_chat_config = serializers.SerializerMethodField()
    url_chatapp = serializers.SerializerMethodField()
    ready = serializers.SerializerMethodField()

    class Meta:
        model = ChatBot
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields

    def get_functions(self, obj: ChatBot):
        qs = ChatBotFunctions.objects.filter(chatbot=obj)
        return ChatBotFunctionsSerializer(qs, many=True).data

    def get_plugins(self, obj: ChatBot):
        qs = ChatBotPlugin.objects.filter(chatbot=obj)
        return ChatBotPluginMiniSerializer(qs, many=True).data

    def get_custom_domains(self, obj: ChatBot):
        qs = ChatBotCustomDomain.objects.filter(chatbot=obj)
        return ChatBotCustomDomainSerializer(qs, many=True).data

    def get_api_keys(self, obj: ChatBot):
        qs = ChatBotAPIKey.objects.filter(chatbot=obj)
        return ChatBotAPIKeySerializer(qs, many=True).data

    def get_hashed_id(self, obj: ChatBot):
        return obj.hashed_id

    def get_rfc1034_compliant_name(self, obj: ChatBot):
        return obj.rfc1034_compliant_name

    def get_default_system_role(self, obj: ChatBot):
        return obj.default_system_role_enhanced

    def get_base_api_domain(self, obj: ChatBot):
        return obj.base_api_domain

    def get_base_default_host(self, obj: ChatBot):
        return obj.base_default_host

    def get_default_host(self, obj: ChatBot):
        return obj.default_host

    def get_default_url(self, obj: ChatBot):
        return obj.default_url

    def get_custom_host(self, obj: ChatBot):
        return obj.custom_host

    def get_custom_url(self, obj: ChatBot):
        return obj.custom_url

    def get_sandbox_host(self, obj: ChatBot):
        return obj.sandbox_host

    def get_sandbox_url(self, obj: ChatBot):
        return obj.sandbox_url

    def get_hostname(self, obj: ChatBot):
        return obj.hostname

    def get_url(self, obj: ChatBot):
        return obj.url

    def get_url_chatbot(self, obj: ChatBot):
        return obj.url_chatbot

    def get_url_chat_config(self, obj: ChatBot):
        return obj.url_chat_config

    def get_url_chatapp(self, obj: ChatBot):
        return obj.url_chatapp

    def get_ready(self, obj: ChatBot):
        return obj.ready


__all__ = [
    "ChatBotRequestsSerializer",
    "ChatBotSerializer",
    "ChatBotConfigSerializer",
    "ChatBotAPIKeySerializer",
    "ChatBotPluginSerializer",
    "ChatBotFunctionsSerializer",
    "ChatBotCustomDomainSerializer",
]
