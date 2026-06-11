# pylint: disable=W0707,W0718,C0115,W0613
"""Account views for smarter api."""

from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.prompt.api.v1.serializers import (
    ChatHistorySerializer,
    PromptPluginUsageSerializer,
    PromptSerializer,
    PromptToolCallSerializer,
)
from smarter.apps.prompt.models import (
    Chat,
    PromptHistory,
    PromptPluginUsage,
    PromptToolCall,
)
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
    SmarterAuthenticatedListAPIView,
)


class ChatToolCallHistoryListView(SmarterAuthenticatedListAPIView):
    queryset = PromptToolCall.objects.all()
    serializer_class = PromptToolCallSerializer


class ChatToolCallHistoryView(SmarterAuthenticatedAPIView):

    def get(self, request: Request, *args, **kwargs):
        instance = get_object_or_404(PromptToolCall, pk=kwargs["pk"])
        serializer = PromptToolCallSerializer(instance)
        return Response(serializer.data)


class PluginUsageHistoryListView(SmarterAuthenticatedListAPIView):
    queryset = PromptPluginUsage.objects.all()
    serializer_class = PromptPluginUsageSerializer


class PluginUsageHistoryView(SmarterAuthenticatedAPIView):

    def get(self, request: Request, *args, **kwargs):
        instance = get_object_or_404(PluginUsageHistoryView, pk=kwargs["pk"])
        serializer = PromptPluginUsageSerializer(instance)
        return Response(serializer.data)


class ChatHistoryListView(SmarterAuthenticatedListAPIView):
    queryset = Chat.objects.all()
    serializer_class = PromptSerializer


class ChatHistoryView(SmarterAuthenticatedAPIView):

    def get(self, request: Request, *args, **kwargs):
        instance = get_object_or_404(PromptHistory, pk=kwargs["pk"])
        serializer = ChatHistorySerializer(instance)
        return Response(serializer.data)
