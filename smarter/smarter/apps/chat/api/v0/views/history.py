# -*- coding: utf-8 -*-
# pylint: disable=W0707,W0718,C0115
"""Account views for smarter api."""

from rest_framework import generics

from smarter.apps.chat.models import (
    ChatHistory,
    ChatToolCallHistory,
    PluginUsageHistory,
)
from smarter.apps.chat.serializers import (
    ChatHistorySerializer,
    ChatToolCallHistorySerializer,
    PluginUsageHistorySerializer,
)


class ChatToolCallHistoryListCreateView(generics.ListCreateAPIView):
    queryset = ChatToolCallHistory.objects.all()
    serializer_class = ChatToolCallHistorySerializer


class ChatToolCallHistoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ChatToolCallHistory.objects.all()
    serializer_class = ChatToolCallHistorySerializer


class PluginUsageHistoryListCreateView(generics.ListCreateAPIView):
    queryset = PluginUsageHistory.objects.all()
    serializer_class = PluginUsageHistorySerializer


class PluginUsageHistoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PluginUsageHistory.objects.all()
    serializer_class = PluginUsageHistorySerializer


class ChatHistoryListCreateView(generics.ListCreateAPIView):
    queryset = ChatHistory.objects.all()
    serializer_class = ChatHistorySerializer


class ChatHistoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ChatHistory.objects.all()
    serializer_class = ChatHistorySerializer
