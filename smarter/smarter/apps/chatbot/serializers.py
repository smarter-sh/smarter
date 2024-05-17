# pylint: disable=missing-class-docstring
"""Chatbot serializers."""
from rest_framework import serializers

from .models import ChatBot


class ChatBotSerializer(serializers.ModelSerializer):

    class Meta:
        model = ChatBot
        fields = "__all__"
