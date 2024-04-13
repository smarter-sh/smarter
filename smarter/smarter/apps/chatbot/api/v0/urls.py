"""URL configuration for chat app."""

from django.urls import path

from .views.chatbot import (
    ChatBotAPIKeyListView,
    ChatBotAPIKeyView,
    ChatBotCustomDomainListView,
    ChatBotCustomDomainView,
    ChatBotFunctionsListView,
    ChatBotFunctionsView,
    ChatBotListView,
    ChatBotPluginListView,
    ChatBotPluginView,
    ChatBotView,
)
from .views.smarter import SmarterChatViewSet


urlpatterns = [
    path("chatbot", SmarterChatViewSet.as_view(), name="smarter-chat-api"),
    # TO DO: add paths for langchain, openai and other chatbot providers
    path("chatbots", ChatBotListView.as_view(), name="chatbot-api"),
    path("chatbot/<int:chatbot_id>", ChatBotView.as_view(), name="chatbot-api"),
    path("chatbot/<int:chatbot_id>/plugins", ChatBotPluginListView.as_view(), name="chatbot-api-plugins"),
    path("chatbot/<int:chatbot_id>/plugins/<int:plugin_id>", ChatBotPluginView.as_view(), name="chatbot-api-plugin"),
    path("chatbot/<int:chatbot_id>/apikeys", ChatBotAPIKeyListView.as_view(), name="chatbot-api-apikeys"),
    path("chatbot/<int:chatbot_id>/apikeys/<int:apikey_id>", ChatBotAPIKeyView.as_view(), name="chatbot-api-apikey"),
    path(
        "chatbot/<int:chatbot_id>/customdomains",
        ChatBotCustomDomainListView.as_view(),
        name="chatbot-api-customdomains",
    ),
    path(
        "chatbot/<int:chatbot_id>/customdomains/<int:customdomain_id>",
        ChatBotCustomDomainView.as_view(),
        name="chatbot-api-customdomain",
    ),
    path("chatbot/<int:chatbot_id>/functions", ChatBotFunctionsListView.as_view(), name="chatbot-api-functions"),
    path(
        "chatbot/<int:chatbot_id>/functions/<int:function_id>",
        ChatBotFunctionsView.as_view(),
        name="chatbot-api-function",
    ),
    path(
        "chatbot/<int:chatbot_id>/functions/<int:function_id>/plugins",
        ChatBotPluginListView.as_view(),
        name="chatbot-api-function-plugins",
    ),
]
