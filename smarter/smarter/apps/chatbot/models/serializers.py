# pylint: disable=W0613,C0115,C0302
"""All models for the OpenAI Function Calling API app."""

from rest_framework import serializers

from smarter.apps.account.serializers import UserProfileSerializer
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .chatbot import ChatBot
from .chatbot_custom_domain import ChatBotCustomDomain
from .chatbot_requests import ChatBotRequests

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CHATBOT_LOGGING])


class ChatBotRequestsSerializer(serializers.ModelSerializer):

    class Meta:
        model = ChatBotRequests
        fields = (
            "id",
            "created_at",
            "updated_at",
            "request",
            "is_aggregation",
        )


class ChatBotSerializer(serializers.ModelSerializer):
    url_chatbot = serializers.ReadOnlyField()
    user_profile = UserProfileSerializer()

    class Meta:
        model = ChatBot
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Meta.fields = [
            field.name
            for field in self.Meta.model._meta.get_fields()
            if field.name not in ["chat", "chatbotapikey", "chatbotplugin", "chatbotfunctions", "chatbotrequests"]
        ]
        self.Meta.fields += ["url_chatbot", "user_profile"]


class ChatBotCustomDomainSerializer(serializers.ModelSerializer):

    class Meta:
        model = ChatBotCustomDomain
        fields = "__all__"


__all__ = [
    "ChatBotRequestsSerializer",
    "ChatBotSerializer",
    "ChatBotCustomDomainSerializer",
]
