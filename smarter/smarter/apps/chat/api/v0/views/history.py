# pylint: disable=W0707,W0718,C0115,W0613
"""Account views for smarter api."""
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from smarter.apps.chat.api.v0.serializers import (
    ChatHistorySerializer,
    ChatToolCallHistorySerializer,
    PluginUsageHistorySerializer,
)
from smarter.apps.chat.models import (
    ChatHistory,
    ChatToolCallHistory,
    PluginUsageHistory,
)
from smarter.lib.drf.view_helpers import (
    SmarterAuthenticatedAPIListView,
    SmarterAuthenticatedAPIView,
)


class ChatToolCallHistoryListView(SmarterAuthenticatedAPIListView):
    queryset = ChatToolCallHistory.objects.all()
    serializer_class = ChatToolCallHistorySerializer


class ChatToolCallHistoryView(SmarterAuthenticatedAPIView):

    def get(self, request, *args, **kwargs):
        instance = get_object_or_404(ChatToolCallHistory, pk=kwargs["pk"])
        serializer = ChatToolCallHistorySerializer(instance)
        return Response(serializer.data)


class PluginUsageHistoryListView(SmarterAuthenticatedAPIListView):
    queryset = PluginUsageHistory.objects.all()
    serializer_class = PluginUsageHistorySerializer


class PluginUsageHistoryView(SmarterAuthenticatedAPIView):

    def get(self, request, *args, **kwargs):
        instance = get_object_or_404(PluginUsageHistoryView, pk=kwargs["pk"])
        serializer = PluginUsageHistorySerializer(instance)
        return Response(serializer.data)


class ChatHistoryListView(SmarterAuthenticatedAPIListView):
    queryset = ChatHistory.objects.all()
    serializer_class = ChatHistorySerializer


class ChatHistoryView(SmarterAuthenticatedAPIView):

    def get(self, request, *args, **kwargs):
        instance = get_object_or_404(ChatHistory, pk=kwargs["pk"])
        serializer = ChatHistorySerializer(instance)
        return Response(serializer.data)
