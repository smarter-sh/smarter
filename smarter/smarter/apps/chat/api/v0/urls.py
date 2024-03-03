# -*- coding: utf-8 -*-
"""URL configuration for chat app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views.chat import FunctionCallingViewSet
from .views.history import (
    ChatHistoryListCreateView,
    ChatHistoryRetrieveUpdateDestroyView,
    ChatToolCallHistoryListCreateView,
    ChatToolCallHistoryRetrieveUpdateDestroyView,
    PluginUsageHistoryListCreateView,
    PluginUsageHistoryRetrieveUpdateDestroyView,
)


# Routers provide an easy way of automatically determining the URL conf.
router = DefaultRouter()

router.register(r"", FunctionCallingViewSet, basename="chat")

urlpatterns = [
    path("", include(router.urls)),
    path("history/chats/", ChatHistoryListCreateView.as_view(), name="chathistory_list_create"),
    path(
        "history/chats/<int:pk>/",
        ChatHistoryRetrieveUpdateDestroyView.as_view(),
        name="chathistory_retrieve_update_destroy",
    ),
    path("history/tool-calls/", ChatToolCallHistoryListCreateView.as_view(), name="chattoolcallhistory_list_create"),
    path(
        "history/tool-calls/<int:pk>/",
        ChatToolCallHistoryRetrieveUpdateDestroyView.as_view(),
        name="chattoolcallhistory_retrieve_update_destroy",
    ),
    path("history/plugin-usage/", PluginUsageHistoryListCreateView.as_view(), name="pluginusagehistory_list_create"),
    path(
        "history/plugin-usage/<int:pk>/",
        PluginUsageHistoryRetrieveUpdateDestroyView.as_view(),
        name="pluginusagehistory_retrieve_update_destroy",
    ),
]
