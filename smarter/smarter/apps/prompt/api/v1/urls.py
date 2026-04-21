"""URL configuration for chat app."""

from django.urls import include, path

from .const import namespace
from .views.chat import urls as chat_urls
from .views.chat.const import namespace as chat_namespace
from .views.history import (
    ChatHistoryListView,
    ChatHistoryView,
    ChatToolCallHistoryListView,
    ChatToolCallHistoryView,
    PluginUsageHistoryListView,
    PluginUsageHistoryView,
)

app_name = namespace

urlpatterns = [
    path("", include(chat_urls, chat_namespace)),
    path("history/chat/", ChatHistoryListView.as_view(), name="chathistory_list"),
    path(
        "history/chat/<int:pk>/",
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
