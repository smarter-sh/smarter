"""URL configuration for chat app."""

from django.urls import path

from smarter.apps.prompt.views import ChatConfigView
from smarter.common.utils import camel_case_object_name

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
BY_ID = "by_id"
BY_HASHED_ID = "by_hashed_id"


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

    namespace = f"api:{namespace}:chatbot"

    # reverse() by hashed_id
    # --------------------------------------------------------------------------
    chatbot_view_by_hashed_id = camel_case_object_name(ChatbotView) + BY_HASHED_ID
    chat_config_view_by_hashed_id = camel_case_object_name(ChatConfigView) + BY_HASHED_ID
    default_chatbot_api_view_by_hashed_id = camel_case_object_name(DefaultChatbotApiView) + BY_HASHED_ID

    # legacy reverse() references by chatbot_id
    # --------------------------------------------------------------------------
    chat_config_view_by_id = camel_case_object_name(ChatConfigView)
    default_chatbot_api_view_by_id = camel_case_object_name(DefaultChatbotApiView)

    # currently no reverse() references to these named views.
    # --------------------------------------------------------------------------
    chatbot_list_view = camel_case_object_name(ChatbotListView)
    chatbot_view_by_id = camel_case_object_name(ChatbotView) + BY_ID
    chatbot_plugin_list_view_by_id = camel_case_object_name(ChatbotPluginListView) + BY_ID
    chatbot_plugin_view_by_id = camel_case_object_name(ChatbotPluginView) + BY_ID
    chatbot_api_key_list_view_by_id = camel_case_object_name(ChatbotAPIKeyListView) + BY_ID
    chatbot_api_key_view_by_id = camel_case_object_name(ChatbotAPIKeyView) + BY_ID
    chatbot_custom_domain_list_view_by_id = camel_case_object_name(ChatbotCustomDomainListView) + BY_ID
    chatbot_custom_domain_view_by_id = camel_case_object_name(ChatbotCustomDomainView) + BY_ID
    chatbot_api_functions_by_id = camel_case_object_name(ChatBotFunctionsListView) + BY_ID
    chatbot_functions_view_by_id = camel_case_object_name(ChatbotFunctionsView) + BY_ID
    chatbot_function_plugin_list_view_by_id = camel_case_object_name(ChatbotPluginListView) + BY_ID


urlpatterns = [
    path("", ChatbotListView.as_view(), name=ChatBotApiV1ReverseViews.chatbot_list_view),
    # --------------------------------------------------------------------------
    # paths by hashed_id
    # --------------------------------------------------------------------------
    path("<str:hashed_id>/", ChatbotView.as_view(), name=ChatBotApiV1ReverseViews.chatbot_view_by_hashed_id),
    path(
        "<str:hashed_id>/config/", ChatConfigView.as_view(), name=ChatBotApiV1ReverseViews.chat_config_view_by_hashed_id
    ),
    path(
        "<str:hashed_id>/chat/",
        DefaultChatbotApiView.as_view(),
        name=ChatBotApiV1ReverseViews.default_chatbot_api_view_by_hashed_id,
    ),
    # mcdaniel: this is a patch to keep the react component working with the new hashed_id urls.
    path("<str:hashed_id>/chat/config/", ChatConfigView.as_view()),
    # --------------------------------------------------------------------------
    # paths by chatbot_id
    # --------------------------------------------------------------------------
    path("<int:chatbot_id>/", ChatbotView.as_view(), name=ChatBotApiV1ReverseViews.chatbot_view_by_id),
    path("<int:chatbot_id>/config/", ChatConfigView.as_view(), name=ChatBotApiV1ReverseViews.chat_config_view_by_id),
    path(
        "<int:chatbot_id>/chat/",
        DefaultChatbotApiView.as_view(),
        name=ChatBotApiV1ReverseViews.default_chatbot_api_view_by_id,
    ),
    # --------------------------------------------------------------------------
    # paths by chatbot_id that are not currently referenced by reverse()
    # in the codebase
    # --------------------------------------------------------------------------
    path("<int:chatbot_id>/chat/config/", ChatConfigView.as_view(), name="chat_config_view_legacy"),
    path(
        "<int:chatbot_id>/plugins/",
        ChatbotPluginListView.as_view(),
        name=ChatBotApiV1ReverseViews.chatbot_plugin_list_view_by_id,
    ),
    path(
        "<int:chatbot_id>/plugins/<int:plugin_id>/",
        ChatbotPluginView.as_view(),
        name=ChatBotApiV1ReverseViews.chatbot_plugin_view_by_id,
    ),
    path(
        "<int:chatbot_id>/apikeys/",
        ChatbotAPIKeyListView.as_view(),
        name=ChatBotApiV1ReverseViews.chatbot_api_key_list_view_by_id,
    ),
    path(
        "<int:chatbot_id>/apikeys/<int:apikey_id>/",
        ChatbotAPIKeyView.as_view(),
        name=ChatBotApiV1ReverseViews.chatbot_api_key_view_by_id,
    ),
    path(
        "<int:chatbot_id>/customdomains",
        ChatbotCustomDomainListView.as_view(),
        name=ChatBotApiV1ReverseViews.chatbot_custom_domain_list_view_by_id,
    ),
    path(
        "<int:chatbot_id>/customdomains/<int:customdomain_id>",
        ChatbotCustomDomainView.as_view(),
        name=ChatBotApiV1ReverseViews.chatbot_custom_domain_view_by_id,
    ),
    path(
        "<int:chatbot_id>/functions",
        ChatBotFunctionsListView.as_view(),
        name=ChatBotApiV1ReverseViews.chatbot_api_functions_by_id,
    ),
    path(
        "<int:chatbot_id>/functions/<int:function_id>",
        ChatbotFunctionsView.as_view(),
        name=ChatBotApiV1ReverseViews.chatbot_functions_view_by_id,
    ),
    path(
        "<int:chatbot_id>/functions/<int:function_id>/plugins",
        ChatbotPluginListView.as_view(),
        name=ChatBotApiV1ReverseViews.chatbot_function_plugin_list_view_by_id,
    ),
]
