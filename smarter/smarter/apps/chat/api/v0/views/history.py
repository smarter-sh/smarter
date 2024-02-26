# -*- coding: utf-8 -*-
# pylint: disable=W0707,W0718
"""Account views for smarter api."""
from http import HTTPStatus

from django.http import JsonResponse
from knox.auth import TokenAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from smarter.apps.account.models import Account, UserProfile
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def chat_history_view(request, account_id: int = None):
    if request.method == "GET":
        return get_chat_history(request, account_id)
    return JsonResponse({"error": "Invalid HTTP method"}, status=405)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def plugin_usage_history_view(request, plugin_id: int = None):
    if request.method == "GET":
        return get_plugin_usage_history(request, plugin_id=plugin_id)
    return JsonResponse({"error": "Invalid HTTP method"}, status=405)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication, SessionAuthentication])
def chat_tool_call_history_view(request, plugin_id: int = None):
    if request.method == "GET":
        return get_chat_tool_call_history(request, plugin_id=plugin_id)
    return JsonResponse({"error": "Invalid HTTP method"}, status=405)


# -----------------------------------------------------------------------
# handlers for accounts
# -----------------------------------------------------------------------
# pylint: disable=unused-argument
def get_chat_tool_call_history(request, plugin_id: int = None):
    chat_tool_call_history = ChatToolCallHistory.objects.filter(plugin=plugin_id)
    serializer = ChatToolCallHistorySerializer(chat_tool_call_history, many=True)
    return Response(serializer.data, status=HTTPStatus.OK)


# pylint: disable=unused-argument
def get_plugin_usage_history(request, plugin_id: int = None):
    plugin_usage_history = PluginUsageHistory.objects.filter(plugin=plugin_id)
    serializer = PluginUsageHistorySerializer(plugin_usage_history, many=True)
    return Response(serializer.data, status=HTTPStatus.OK)


def get_chat_history(request, account_id: int = None):
    """Get an account json representation by id."""
    try:
        if account_id:
            account = Account.objects.get(id=account_id)
        else:
            account = UserProfile.objects.get(user=request.user).account
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    chat_history = ChatHistory.objects.filter(user=account.user)
    serializer = ChatHistorySerializer(chat_history)
    return Response(serializer.data, status=HTTPStatus.OK)
