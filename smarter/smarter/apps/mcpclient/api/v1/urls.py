"""URL configuration for mcpclient app API."""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.default import DefaultMCPClientApiView
from .views.views import (
    MCPClientListView,
    MCPClientView,
)

app_name = namespace
BY_ID = "by_id"
BY_HASHED_ID = "by_hashed_id"


class MCPClientApiV1ReverseViews:
    """
    Reverse views for the MCPClient CLI commands.

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

    namespace = f"api:{namespace}:mcpclient"

    # reverse() by hashed_id
    # --------------------------------------------------------------------------
    mcpclient_view_by_hashed_id = to_snake_case(MCPClientView.__name__) + BY_HASHED_ID
    default_mcpclient_api_view_by_hashed_id = to_snake_case(DefaultMCPClientApiView.__name__) + BY_HASHED_ID

    # legacy reverse() references by mcpclient_id
    # --------------------------------------------------------------------------
    default_mcpclient_api_view_by_id = to_snake_case(DefaultMCPClientApiView.__name__)

    # currently no reverse() references to these named views.
    # --------------------------------------------------------------------------
    mcpclient_list_view = to_snake_case(MCPClientListView.__name__)
    mcpclient_view_by_id = to_snake_case(MCPClientView.__name__) + BY_ID


urlpatterns = [
    path("", MCPClientListView.as_view(), name=MCPClientApiV1ReverseViews.mcpclient_list_view),
    # --------------------------------------------------------------------------
    # paths by hashed_id
    # --------------------------------------------------------------------------
    path("<str:hashed_id>/", MCPClientView.as_view(), name=MCPClientApiV1ReverseViews.mcpclient_view_by_hashed_id),
    path(
        "<str:hashed_id>/mcpclient/",
        DefaultMCPClientApiView.as_view(),
        name=MCPClientApiV1ReverseViews.default_mcpclient_api_view_by_hashed_id,
    ),
    # --------------------------------------------------------------------------
    # paths by mcpclient_id
    # --------------------------------------------------------------------------
    path("<int:mcpclient_id>/", MCPClientView.as_view(), name=MCPClientApiV1ReverseViews.mcpclient_view_by_id),
    path(
        "<int:mcpclient_id>/mcpclient/",
        DefaultMCPClientApiView.as_view(),
        name=MCPClientApiV1ReverseViews.default_mcpclient_api_view_by_id,
    ),
]
