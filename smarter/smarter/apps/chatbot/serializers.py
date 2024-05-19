# pylint: disable=missing-class-docstring
"""Chatbot serializers."""
from rest_framework import serializers

from .models import ChatBot, ChatBotAPIKey, ChatBotCustomDomain, ChatBotPlugin


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

    class Meta:
        model = ChatBotPlugin
        fields = "__all__"
