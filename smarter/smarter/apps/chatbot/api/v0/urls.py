"""URL configuration for chat app."""

from django.urls import path

from smarter.apps.chatbot.deployments.smarter import SmarterChatBotApiViewSet

from .views import (
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


urlpatterns = [
    # TO DO: add paths for langchain, openai and other chatbot providers
    path("", ChatBotListView.as_view(), name="chatbot-api"),
    path("<int:chatbot_id>/", ChatBotView.as_view(), name="chatbot-api"),
    path("<int:chatbot_id>/chatbot/", SmarterChatBotApiViewSet.as_view(), name="chatbot-api-chatbot"),
    path("<int:chatbot_id>/plugins/", ChatBotPluginListView.as_view(), name="chatbot-api-plugins"),
    path("<int:chatbot_id>/plugins/<int:plugin_id>/", ChatBotPluginView.as_view(), name="chatbot-api-plugin"),
    path("<int:chatbot_id>/apikeys/", ChatBotAPIKeyListView.as_view(), name="chatbot-api-apikeys"),
    path("<int:chatbot_id>/apikeys/<int:apikey_id>/", ChatBotAPIKeyView.as_view(), name="chatbot-api-apikey"),
    path(
        "<int:chatbot_id>/customdomains",
        ChatBotCustomDomainListView.as_view(),
        name="chatbot-api-customdomains",
    ),
    path(
        "<int:chatbot_id>/customdomains/<int:customdomain_id>",
        ChatBotCustomDomainView.as_view(),
        name="chatbot-api-customdomain",
    ),
    path("<int:chatbot_id>/functions", ChatBotFunctionsListView.as_view(), name="chatbot-api-functions"),
    path(
        "<int:chatbot_id>/functions/<int:function_id>",
        ChatBotFunctionsView.as_view(),
        name="chatbot-api-function",
    ),
    path(
        "<int:chatbot_id>/functions/<int:function_id>/plugins",
        ChatBotPluginListView.as_view(),
        name="chatbot-api-function-plugins",
    ),
]
