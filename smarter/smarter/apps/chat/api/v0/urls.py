# -*- coding: utf-8 -*-
"""URL configuration for chat app."""

from django.urls import path

from .views.chat import SmarterChatViewSet
from .views.history import (
    ChatHistoryListView,
    ChatHistoryView,
    ChatToolCallHistoryListView,
    ChatToolCallHistoryView,
    PluginUsageHistoryListView,
    PluginUsageHistoryView,
)


urlpatterns = [
    path("", SmarterChatViewSet.as_view(), name="chat"),
    path("history/chats/", ChatHistoryListView.as_view(), name="chathistory_list"),
    path(
        "history/chats/<int:pk>/",
        ChatHistoryView.as_view(),
        name="chathistory",
    ),
    path("history/tool-calls/", ChatToolCallHistoryListView.as_view(), name="chattoolcallhistory_list"),
    path(
        "history/tool-calls/<int:pk>/",
        ChatToolCallHistoryView.as_view(),
        name="chattoolcallhistory",
    ),
    path("history/plugin-usage/", PluginUsageHistoryListView.as_view(), name="pluginusagehistory_list"),
    path(
        "history/plugin-usage/<int:pk>/",
        PluginUsageHistoryView.as_view(),
        name="pluginusagehistory",
    ),
]
