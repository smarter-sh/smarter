"""URL configuration for chat app."""

from django.urls import path

from smarter.apps.prompt.views.detailviews import PromptConfigView
from smarter.common.utils import to_snake_case

from .const import namespace
from .views.default import DefaultLLMClientApiView
from .views.views import (
    LLMClientAPIKeyListView,
    LLMClientAPIKeyView,
    LLMClientCustomDomainListView,
    LLMClientCustomDomainView,
    LLMClientFunctionsListView,
    LLMClientFunctionsView,
    LLMClientListView,
    LLMClientPluginListView,
    LLMClientPluginView,
    LLMClientView,
)

app_name = namespace
BY_ID = "by_id"
BY_HASHED_ID = "by_hashed_id"


class LLMClientApiV1ReverseViews:
    """
    Reverse views for the LLMClient CLI commands.

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

        from smarter.lib.django.shortcuts import reverse
        url = reverse(ApiV1CliReverseViews.deploy, kwargs={'kind': 'Plugin'})

        str(ApiV1CliReverseViews.deploy)
        returns 'api_v1_cli_deploy_api_view'
    """

    namespace = f"api:{namespace}:llm_client"

    # reverse() by hashed_id
    # --------------------------------------------------------------------------
    llm_client_view_by_hashed_id = to_snake_case(LLMClientView) + BY_HASHED_ID
    chat_config_view_by_hashed_id = to_snake_case(PromptConfigView) + BY_HASHED_ID
    default_llm_client_api_view_by_hashed_id = to_snake_case(DefaultLLMClientApiView) + BY_HASHED_ID

    # legacy reverse() references by llm_client_id
    # --------------------------------------------------------------------------
    chat_config_view_by_id = to_snake_case(PromptConfigView)
    default_llm_client_api_view_by_id = to_snake_case(DefaultLLMClientApiView)

    # currently no reverse() references to these named views.
    # --------------------------------------------------------------------------
    llm_client_list_view = to_snake_case(LLMClientListView)
    llm_client_view_by_id = to_snake_case(LLMClientView) + BY_ID
    llm_client_plugin_list_view_by_id = to_snake_case(LLMClientPluginListView) + BY_ID
    llm_client_plugin_view_by_id = to_snake_case(LLMClientPluginView) + BY_ID
    llm_client_api_key_list_view_by_id = to_snake_case(LLMClientAPIKeyListView) + BY_ID
    llm_client_api_key_view_by_id = to_snake_case(LLMClientAPIKeyView) + BY_ID
    llm_client_custom_domain_list_view_by_id = to_snake_case(LLMClientCustomDomainListView) + BY_ID
    llm_client_custom_domain_view_by_id = to_snake_case(LLMClientCustomDomainView) + BY_ID
    llm_client_api_functions_by_id = to_snake_case(LLMClientFunctionsListView) + BY_ID
    llm_client_functions_view_by_id = to_snake_case(LLMClientFunctionsView) + BY_ID
    llm_client_function_plugin_list_view_by_id = to_snake_case(LLMClientPluginListView) + BY_ID


urlpatterns = [
    path("", LLMClientListView.as_view(), name=LLMClientApiV1ReverseViews.llm_client_list_view),
    # --------------------------------------------------------------------------
    # paths by hashed_id
    # --------------------------------------------------------------------------
    path("<str:hashed_id>/", LLMClientView.as_view(), name=LLMClientApiV1ReverseViews.llm_client_view_by_hashed_id),
    path(
        "<str:hashed_id>/config/",
        PromptConfigView.as_view(),
        name=LLMClientApiV1ReverseViews.chat_config_view_by_hashed_id,
    ),
    path(
        "<str:hashed_id>/chat/",
        DefaultLLMClientApiView.as_view(),
        name=LLMClientApiV1ReverseViews.default_llm_client_api_view_by_hashed_id,
    ),
    # mcdaniel: this is a patch to keep the react component working with the new hashed_id urls.
    path("<str:hashed_id>/chat/config/", PromptConfigView.as_view()),
    # --------------------------------------------------------------------------
    # paths by llm_client_id
    # --------------------------------------------------------------------------
    path("<int:llm_client_id>/", LLMClientView.as_view(), name=LLMClientApiV1ReverseViews.llm_client_view_by_id),
    path(
        "<int:llm_client_id>/config/",
        PromptConfigView.as_view(),
        name=LLMClientApiV1ReverseViews.chat_config_view_by_id,
    ),
    path(
        "<int:llm_client_id>/chat/",
        DefaultLLMClientApiView.as_view(),
        name=LLMClientApiV1ReverseViews.default_llm_client_api_view_by_id,
    ),
    # --------------------------------------------------------------------------
    # paths by llm_client_id that are not currently referenced by reverse()
    # in the codebase
    # --------------------------------------------------------------------------
    path("<int:llm_client_id>/chat/config/", PromptConfigView.as_view(), name="chat_config_view_legacy"),
    path(
        "<int:llm_client_id>/plugins/",
        LLMClientPluginListView.as_view(),
        name=LLMClientApiV1ReverseViews.llm_client_plugin_list_view_by_id,
    ),
    path(
        "<int:llm_client_id>/plugins/<int:plugin_id>/",
        LLMClientPluginView.as_view(),
        name=LLMClientApiV1ReverseViews.llm_client_plugin_view_by_id,
    ),
    path(
        "<int:llm_client_id>/apikeys/",
        LLMClientAPIKeyListView.as_view(),
        name=LLMClientApiV1ReverseViews.llm_client_api_key_list_view_by_id,
    ),
    path(
        "<int:llm_client_id>/apikeys/<int:apikey_id>/",
        LLMClientAPIKeyView.as_view(),
        name=LLMClientApiV1ReverseViews.llm_client_api_key_view_by_id,
    ),
    path(
        "<int:llm_client_id>/customdomains",
        LLMClientCustomDomainListView.as_view(),
        name=LLMClientApiV1ReverseViews.llm_client_custom_domain_list_view_by_id,
    ),
    path(
        "<int:llm_client_id>/customdomains/<int:customdomain_id>",
        LLMClientCustomDomainView.as_view(),
        name=LLMClientApiV1ReverseViews.llm_client_custom_domain_view_by_id,
    ),
    path(
        "<int:llm_client_id>/functions",
        LLMClientFunctionsListView.as_view(),
        name=LLMClientApiV1ReverseViews.llm_client_api_functions_by_id,
    ),
    path(
        "<int:llm_client_id>/functions/<int:function_id>",
        LLMClientFunctionsView.as_view(),
        name=LLMClientApiV1ReverseViews.llm_client_functions_view_by_id,
    ),
    path(
        "<int:llm_client_id>/functions/<int:function_id>/plugins",
        LLMClientPluginListView.as_view(),
        name=LLMClientApiV1ReverseViews.llm_client_function_plugin_list_view_by_id,
    ),
]
