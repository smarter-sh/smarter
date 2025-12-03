"""URL configuration for chat app."""

from django.urls import path

from smarter.apps.prompt.views import ChatConfigView

from .const import namespace
from .views.default import DefaultChatbotApiView
from .views.views import (
    ChatbotAPIKeyListView,
    ChatbotAPIKeyView,
    ChatbotCustomDomainListView,
    ChatbotCustomDomainView,
    ChatBotFunctionsListView,
    ChatbotFunctionsView,
    ChatbotListView,
    ChatbotPluginListView,
    ChatbotPluginView,
    ChatbotView,
)


app_name = namespace


urlpatterns = [
    path("", ChatbotListView.as_view(), name="chatbot_list_view"),
    path("<int:chatbot_id>/", ChatbotView.as_view(), name="chatbot_view"),
    path("<int:chatbot_id>/config/", ChatConfigView.as_view(), name="chat_config_view"),
    path("<int:chatbot_id>/chat/", DefaultChatbotApiView.as_view(), name="default_chatbot_api_view"),
    path("<int:chatbot_id>/chat/config/", ChatConfigView.as_view(), name="chat_config_view_legacy"),
    path("<int:chatbot_id>/plugins/", ChatbotPluginListView.as_view(), name="chatbot_plugin_list_view"),
    path("<int:chatbot_id>/plugins/<int:plugin_id>/", ChatbotPluginView.as_view(), name="chatbot_plugin_view"),
    path("<int:chatbot_id>/apikeys/", ChatbotAPIKeyListView.as_view(), name="chatbot_api_key_list_view"),
    path("<int:chatbot_id>/apikeys/<int:apikey_id>/", ChatbotAPIKeyView.as_view(), name="chatbot_api_key_view"),
    path(
        "<int:chatbot_id>/customdomains",
        ChatbotCustomDomainListView.as_view(),
        name="chatbot_custom_domain_list_view",
    ),
    path(
        "<int:chatbot_id>/customdomains/<int:customdomain_id>",
        ChatbotCustomDomainView.as_view(),
        name="chatbot_custom_domain_view",
    ),
    path("<int:chatbot_id>/functions", ChatBotFunctionsListView.as_view(), name="chatbot-api-functions"),
    path(
        "<int:chatbot_id>/functions/<int:function_id>",
        ChatbotFunctionsView.as_view(),
        name="chatbot_functions_view",
    ),
    path(
        "<int:chatbot_id>/functions/<int:function_id>/plugins",
        ChatbotPluginListView.as_view(),
        name="chatbot_function_plugin_list_view",
    ),
]
