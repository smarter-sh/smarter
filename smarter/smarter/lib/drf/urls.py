"""URL configuration for the web platform."""

from django.urls import path, re_path

from smarter.common.utils import to_snake_case
from smarter.lib.drf.views.detailview import AuthTokenDetailView
from smarter.lib.drf.views.listview.api import (
    AuthTokenListApiCloneView,
    AuthTokenListApiDeleteView,
    AuthTokenListApiRenameView,
    AuthTokenListApiView,
)
from smarter.lib.drf.views.listview.view import AuthTokenListView

from .const import namespace


class AuthTokenReverseNames:
    """
    Holds named URL patterns for the account dashboard.

    This class provides constants for all named URL patterns used in the account dashboard views.
    """

    namespace = namespace

    listview = to_snake_case(AuthTokenListApiView)
    detailview = to_snake_case(AuthTokenDetailView)

    listview = to_snake_case(AuthTokenListView)
    listview_api = to_snake_case(AuthTokenListApiView)
    listview_api_all = to_snake_case(AuthTokenListApiView) + "_all"
    listview_api_clone = to_snake_case(AuthTokenListApiCloneView)
    listview_api_delete = to_snake_case(AuthTokenListApiDeleteView)
    listview_api_rename = to_snake_case(AuthTokenListApiRenameView)


app_name = namespace

urlpatterns = [
    path("", AuthTokenListView.as_view(), name=AuthTokenReverseNames.listview),
    path(
        "react-integration/api/listview/", AuthTokenListApiView.as_view(), name=AuthTokenReverseNames.listview_api_all
    ),
    re_path(
        r"^react-integration/api/listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        AuthTokenListApiView.as_view(),
        name=AuthTokenReverseNames.listview_api,
    ),
    path(
        "react-integration/api/clone/<int:llm_client_id>/<str:new_name>/",
        AuthTokenListApiCloneView.as_view(),
        name=AuthTokenReverseNames.listview_api_clone,
    ),
    path(
        "react-integration/api/delete/<int:llm_client_id>/",
        AuthTokenListApiDeleteView.as_view(),
        name=AuthTokenReverseNames.listview_api_delete,
    ),
    path(
        "react-integration/api/rename/<int:llm_client_id>/<str:new_name>/",
        AuthTokenListApiRenameView.as_view(),
        name=AuthTokenReverseNames.listview_api_rename,
    ),
    path("<int:authtoken_id>/", AuthTokenDetailView.as_view(), name=AuthTokenReverseNames.detailview),
]
