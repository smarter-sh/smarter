"""
URL configuration for the prompt API, including endpoints for chat interactions and history.
This module defines the URL patterns for the prompt API, which includes routes for chat interactions,
 chat history, tool call history, and plugin usage history. The chat endpoints allow users to interact
 with various LLM providers through a passthrough mechanism, while the history endpoints provide access
 to past interactions and usage data.

 The URL patterns are organized under the 'prompt' namespace and include:

 - /api/v1/prompt/chat/ for chat interactions with LLM providers.
 - /api/v1/prompt/history/chat/ for accessing chat history.
 - /api/v1/prompt/history/tool-calls/ for accessing tool call history.
 - /api/v1/prompt/history/plugin-usage/ for accessing plugin usage history.

 Each endpoint is associated with a specific view that handles the corresponding functionality, such as
 processing chat requests or retrieving historical data. The views are designed to work with authenticated
 users and provide appropriate responses based on the request parameters and user permissions.

 For more details on each endpoint and its expected behavior, refer to the corresponding view implementations
 in the views.chat and views.history modules.
"""

from django.urls import path

from .const import namespace
from .views.history import (
    ChatHistoryListView,
    ChatHistoryView,
    ChatToolCallHistoryListView,
    ChatToolCallHistoryView,
    PluginUsageHistoryListView,
    PluginUsageHistoryView,
)
from .views.passthrough import PassthroughChatViewSet
from .views.smarter import SmarterChatApiViewSet

app_name = namespace


class PromptAPINamespace:
    """Namespace for prompt API endpoints."""

    chat = "chat"
    chathistory_list = "chathistory_list"
    chathistory = "chathistory"
    chattoolcallhistory_list = "chattoolcallhistory_list"
    chattoolcallhistory = "chattoolcallhistory"
    pluginusagehistory_list = "pluginusagehistory_list"
    pluginusagehistory = "pluginusagehistory"
    smarter = "smarter"
    passthrough = "passthrough"


urlpatterns = [
    path("history/chat/", ChatHistoryListView.as_view(), name=PromptAPINamespace.chathistory_list),
    path(
        "history/chat/<int:pk>/",
        ChatHistoryView.as_view(),
        name=PromptAPINamespace.chathistory,
    ),
    path(
        "history/tool-calls/", ChatToolCallHistoryListView.as_view(), name=PromptAPINamespace.chattoolcallhistory_list
    ),
    path(
        "history/tool-calls/<int:pk>/",
        ChatToolCallHistoryView.as_view(),
        name=PromptAPINamespace.chattoolcallhistory,
    ),
    path(
        "history/plugin-usage/", PluginUsageHistoryListView.as_view(), name=PromptAPINamespace.pluginusagehistory_list
    ),
    path(
        "history/plugin-usage/<int:pk>/",
        PluginUsageHistoryView.as_view(),
        name=PromptAPINamespace.pluginusagehistory,
    ),
    path("smarter/<str:provider_name>/", SmarterChatApiViewSet.as_view(), name=PromptAPINamespace.smarter),
    path("passthrough/<str:provider_name>/", PassthroughChatViewSet.as_view(), name=PromptAPINamespace.passthrough),
]
