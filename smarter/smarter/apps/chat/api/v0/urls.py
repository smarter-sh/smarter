# -*- coding: utf-8 -*-
"""URL configuration for chat app."""

from django.urls import include, path
from django.views.decorators.http import require_http_methods
from rest_framework.routers import DefaultRouter

from smarter.apps.langchain_passthrough.views import LanchainViewSet
from smarter.apps.openai_passthrough.views import OpenAIViewSet

from .views.chat import FunctionCallingViewSet
from .views.history import (
    chat_history_view,
    chat_tool_call_history_view,
    plugin_usage_history_view,
)


# Routers provide an easy way of automatically determining the URL conf.
router = DefaultRouter()

router.register(r"", FunctionCallingViewSet, basename="chat")
router.register(r"chatgpt", OpenAIViewSet, basename="chatgpt")
router.register(r"langchain", LanchainViewSet, basename="langchain")

urlpatterns = [
    path("", include(router.urls)),
    path("history/chats/", require_http_methods(["GET"])(chat_history_view), name="chat_history_view"),
    path(
        "history/plugin-usage/",
        require_http_methods(["GET"])(plugin_usage_history_view),
        name="plugin_usage_history_view",
    ),
    path(
        "history/tool-calls/",
        require_http_methods(["GET"])(chat_tool_call_history_view),
        name="chat_tool_call_history_view",
    ),
]
