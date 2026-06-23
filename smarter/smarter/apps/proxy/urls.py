"""URL configuration for proxy app."""

from django.urls import path, re_path

from smarter.apps.proxy.views.detailview import ProxyDetailView
from smarter.apps.proxy.views.listview.api import (
    ProxyListApiCloneView,
    ProxyListApiDeleteView,
    ProxyListApiRenameView,
    ProxyListApiView,
)
from smarter.apps.proxy.views.listview.view import ProxyListView
from smarter.common.utils.conversion import to_snake_case

from .const import namespace

app_name = namespace


class ProxyReverseNames:
    """
    Holds named URL patterns for the proxy app.

    This class provides constants for all named URL patterns used in the proxy app views.
    """

    namespace = namespace

    listview = to_snake_case(ProxyListApiView.__name__)
    detailview = to_snake_case(ProxyDetailView.__name__)

    listview = to_snake_case(ProxyListView.__name__)
    listview_api = to_snake_case(ProxyListApiView.__name__)
    listview_api_all = to_snake_case(ProxyListApiView.__name__) + "_all"
    listview_api_clone = to_snake_case(ProxyListApiCloneView.__name__)
    listview_api_delete = to_snake_case(ProxyListApiDeleteView.__name__)
    listview_api_rename = to_snake_case(ProxyListApiRenameView.__name__)


urlpatterns = [
    path("", ProxyListView.as_view(), name=ProxyReverseNames.listview),
    path("react-integration/api/listview/", ProxyListApiView.as_view(), name=ProxyReverseNames.listview_api_all),
    re_path(
        r"^react-integration/api/listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        ProxyListApiView.as_view(),
        name=ProxyReverseNames.listview_api,
    ),
    path(
        "react-integration/api/clone/<int:llm_client_id>/<str:new_name>/",
        ProxyListApiCloneView.as_view(),
        name=ProxyReverseNames.listview_api_clone,
    ),
    path(
        "react-integration/api/delete/<int:llm_client_id>/",
        ProxyListApiDeleteView.as_view(),
        name=ProxyReverseNames.listview_api_delete,
    ),
    path(
        "react-integration/api/rename/<int:llm_client_id>/<str:new_name>/",
        ProxyListApiRenameView.as_view(),
        name=ProxyReverseNames.listview_api_rename,
    ),
    path("secrets/<str:hashed_id>/", ProxyDetailView.as_view(), name=ProxyReverseNames.detailview),
]
