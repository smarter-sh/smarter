"""URL configuration for chat app."""

from django.urls import path

from smarter.apps.prompt.views import ChatConfigView
from smarter.common.utils import camel_to_snake

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


class ChatBotApiV1ReverseViews:
    """
    Reverse views for the ChatBot CLI commands
    Provides named references for reversing CLI-related API endpoints.

    This class is used for reverse URL resolution in Django, where each attribute
    corresponds to a CLI command endpoint. The names are derived from the actual
    API view class names, ensuring consistency and reducing the risk of typos
    when using Django's URL reversing features.

    All CLI commands available in the Smarter platform are included as attributes
    of this class. This centralizes the reverse URL names for all CLI endpoints,
    making it easier to maintain and reference them throughout the codebase.

    Usage
    -----
    Use these attributes with Django's ``reverse()`` function or in templates
    to generate URLs for CLI API endpoints based on the view class names.

    Example
    -------
    .. code-block:: python

        from django.urls import reverse
        url = reverse(ApiV1CliReverseViews.deploy, kwargs={'kind': 'Plugin'})

        str(ApiV1CliReverseViews.deploy)
        returns 'api_v1_cli_deploy_api_view'

    """

    namespace = f"api:{namespace}:"

    @staticmethod
    def camel_case(obj) -> str:
        """
        Convert CamelCase to snake_case for URL naming.

        :param name: The CamelCase string to convert.
        :return: The converted snake_case string.
        :rtype: str
        """
        return str(camel_to_snake(obj.__name__))

    chatbot_list_view = camel_case(ChatbotListView)
    chatbot_view = camel_case(ChatbotView)
    chat_config_view = camel_case(ChatConfigView)
    default_chatbot_api_view = camel_case(DefaultChatbotApiView)
    chatbot_plugin_list_view = camel_case(ChatbotPluginListView)
    chatbot_plugin_view = camel_case(ChatbotPluginView)
    chatbot_api_key_list_view = camel_case(ChatbotAPIKeyListView)
    chatbot_api_key_view = camel_case(ChatbotAPIKeyView)
    chatbot_custom_domain_list_view = camel_case(ChatbotCustomDomainListView)
    chatbot_custom_domain_view = camel_case(ChatbotCustomDomainView)
    chatbot_api_functions = camel_case(ChatBotFunctionsListView)
    chatbot_functions_view = camel_case(ChatbotFunctionsView)
    chatbot_function_plugin_list_view = camel_case(ChatbotPluginListView)


urlpatterns = [
    path("", ChatbotListView.as_view(), name=ChatBotApiV1ReverseViews.chatbot_list_view),
    path("<int:chatbot_id>/", ChatbotView.as_view(), name=ChatBotApiV1ReverseViews.chatbot_view),
    path("<int:chatbot_id>/config/", ChatConfigView.as_view(), name=ChatBotApiV1ReverseViews.chat_config_view),
    path(
        "<int:chatbot_id>/chat/",
        DefaultChatbotApiView.as_view(),
        name=ChatBotApiV1ReverseViews.default_chatbot_api_view,
    ),
    path("<int:chatbot_id>/chat/config/", ChatConfigView.as_view(), name="chat_config_view_legacy"),
    path(
        "<int:chatbot_id>/plugins/",
        ChatbotPluginListView.as_view(),
        name=ChatBotApiV1ReverseViews.chatbot_plugin_list_view,
    ),
    path(
        "<int:chatbot_id>/plugins/<int:plugin_id>/",
        ChatbotPluginView.as_view(),
        name=ChatBotApiV1ReverseViews.chatbot_plugin_view,
    ),
    path(
        "<int:chatbot_id>/apikeys/",
        ChatbotAPIKeyListView.as_view(),
        name=ChatBotApiV1ReverseViews.chatbot_api_key_list_view,
    ),
    path(
        "<int:chatbot_id>/apikeys/<int:apikey_id>/",
        ChatbotAPIKeyView.as_view(),
        name=ChatBotApiV1ReverseViews.chatbot_api_key_view,
    ),
    path(
        "<int:chatbot_id>/customdomains",
        ChatbotCustomDomainListView.as_view(),
        name=ChatBotApiV1ReverseViews.chatbot_custom_domain_list_view,
    ),
    path(
        "<int:chatbot_id>/customdomains/<int:customdomain_id>",
        ChatbotCustomDomainView.as_view(),
        name=ChatBotApiV1ReverseViews.chatbot_custom_domain_view,
    ),
    path(
        "<int:chatbot_id>/functions",
        ChatBotFunctionsListView.as_view(),
        name=ChatBotApiV1ReverseViews.chatbot_api_functions,
    ),
    path(
        "<int:chatbot_id>/functions/<int:function_id>",
        ChatbotFunctionsView.as_view(),
        name=ChatBotApiV1ReverseViews.chatbot_functions_view,
    ),
    path(
        "<int:chatbot_id>/functions/<int:function_id>/plugins",
        ChatbotPluginListView.as_view(),
        name=ChatBotApiV1ReverseViews.chatbot_function_plugin_list_view,
    ),
]
