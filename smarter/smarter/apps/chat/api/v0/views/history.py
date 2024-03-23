# -*- coding: utf-8 -*-
# pylint: disable=W0707,W0718,C0115,W0613
"""Account views for smarter api."""
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from smarter.smarter.apps.account.view_helpers import SmarterAPIListView, SmarterAPIView

from ....models import ChatHistory, ChatToolCallHistory, PluginUsageHistory
from ....serializers import (
    ChatHistorySerializer,
    ChatToolCallHistorySerializer,
    PluginUsageHistorySerializer,
)


class ChatToolCallHistoryListView(SmarterAPIListView):
    queryset = ChatToolCallHistory.objects.all()
    serializer_class = ChatToolCallHistorySerializer


class ChatToolCallHistoryView(SmarterAPIView):

    def get(self, request, *args, **kwargs):
        instance = get_object_or_404(ChatToolCallHistory, pk=kwargs["pk"])
        serializer = ChatToolCallHistorySerializer(instance)
        return Response(serializer.data)


class PluginUsageHistoryListView(SmarterAPIListView):
    queryset = PluginUsageHistory.objects.all()
    serializer_class = PluginUsageHistorySerializer


class PluginUsageHistoryView(SmarterAPIView):

    def get(self, request, *args, **kwargs):
        instance = get_object_or_404(PluginUsageHistoryView, pk=kwargs["pk"])
        serializer = PluginUsageHistorySerializer(instance)
        return Response(serializer.data)


class ChatHistoryListView(SmarterAPIListView):
    queryset = ChatHistory.objects.all()
    serializer_class = ChatHistorySerializer


class ChatHistoryView(SmarterAPIView):

    def get(self, request, *args, **kwargs):
        instance = get_object_or_404(ChatHistory, pk=kwargs["pk"])
        serializer = ChatHistorySerializer(instance)
        return Response(serializer.data)
