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


class ChatBotSerializer(MetaDataWithOwnershipModelSerializer):
    url_chatbot = serializers.ReadOnlyField()
    user_profile = UserProfileSerializer()
    default_system_role = serializers.SerializerMethodField()
    hashed_id = serializers.SerializerMethodField()

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

    def get_hashed_id(self, obj: ChatBot):
        return obj.hashed_id


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


class ChatBotFunctionsSerializer(SmarterCamelCaseSerializer):

    class Meta:
        model = ChatBotFunctions
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


__all__ = [
    "ChatBotRequestsSerializer",
    "ChatBotSerializer",
    "ChatBotConfigSerializer",
    "ChatBotAPIKeySerializer",
    "ChatBotPluginSerializer",
    "ChatBotFunctionsSerializer",
    "ChatBotCustomDomainSerializer",
]
