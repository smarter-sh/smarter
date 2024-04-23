# pylint: disable=W0707,W0718,C0115,W0613
"""Account views for smarter api."""
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from smarter.apps.chat.api.v0.serializers import (
    ChatPluginUsageSerializer,
    ChatSerializer,
    ChatToolCallSerializer,
)
from smarter.apps.chat.models import Chat, ChatPluginUsage, ChatToolCall
from smarter.lib.drf.view_helpers import (
    SmarterAuthenticatedAPIView,
    SmarterAuthenticatedListAPIView,
)


class ChatToolCallHistoryListView(SmarterAuthenticatedListAPIView):
    queryset = ChatToolCall.objects.all()
    serializer_class = ChatToolCallSerializer


class ChatToolCallHistoryView(SmarterAuthenticatedAPIView):

    def get(self, request, *args, **kwargs):
        instance = get_object_or_404(ChatToolCall, pk=kwargs["pk"])
        serializer = ChatToolCallSerializer(instance)
        return Response(serializer.data)


class PluginUsageHistoryListView(SmarterAuthenticatedListAPIView):
    queryset = ChatPluginUsage.objects.all()
    serializer_class = ChatPluginUsageSerializer


class PluginUsageHistoryView(SmarterAuthenticatedAPIView):

    def get(self, request, *args, **kwargs):
        instance = get_object_or_404(PluginUsageHistoryView, pk=kwargs["pk"])
        serializer = ChatPluginUsageSerializer(instance)
        return Response(serializer.data)


class ChatHistoryListView(SmarterAuthenticatedListAPIView):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer


class ChatHistoryView(SmarterAuthenticatedAPIView):

    def get(self, request, *args, **kwargs):
        instance = get_object_or_404(Chat, pk=kwargs["pk"])
        serializer = ChatSerializer(instance)
        return Response(serializer.data)
