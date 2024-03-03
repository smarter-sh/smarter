# -*- coding: utf-8 -*-
# pylint: disable=W0707,W0718,C0115
"""Account views for smarter api."""

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
from smarter.view_helpers import SmarterAPIListView, SmarterAPIView


class ChatToolCallHistoryListView(SmarterAPIListView):
    queryset = ChatToolCallHistory.objects.all()
    serializer_class = ChatToolCallHistorySerializer


class ChatToolCallHistoryView(SmarterAPIView):
    queryset = ChatToolCallHistory.objects.all()
    serializer_class = ChatToolCallHistorySerializer


class PluginUsageHistoryListView(SmarterAPIListView):
    queryset = PluginUsageHistory.objects.all()
    serializer_class = PluginUsageHistorySerializer


class PluginUsageHistoryView(SmarterAPIView):
    queryset = PluginUsageHistory.objects.all()
    serializer_class = PluginUsageHistorySerializer


class ChatHistoryListView(SmarterAPIListView):
    queryset = ChatHistory.objects.all()
    serializer_class = ChatHistorySerializer


class ChatHistoryView(SmarterAPIView):
    queryset = ChatHistory.objects.all()
    serializer_class = ChatHistorySerializer
