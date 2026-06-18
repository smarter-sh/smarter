"""URL configuration for the web platform."""

from django.urls import path, re_path

from smarter.apps.secret.views.detailview import SecretDetailView
from smarter.apps.secret.views.listview.api import (
    SecretListApiCloneView,
    SecretListApiDeleteView,
    SecretListApiRenameView,
    SecretListApiView,
)
from smarter.apps.secret.views.listview.view import SecretListView
from smarter.common.utils import to_snake_case

from .const import namespace


class SecretReverseNames:
    """
    Holds named URL patterns for the account dashboard.

    This class provides constants for all named URL patterns used in the account dashboard views.
    """

    namespace = namespace

    listview = to_snake_case(SecretListApiView)
    detailview = to_snake_case(SecretDetailView)

    listview = to_snake_case(SecretListView)
    listview_api = to_snake_case(SecretListApiView)
    listview_api_all = to_snake_case(SecretListApiView) + "_all"
    listview_api_clone = to_snake_case(SecretListApiCloneView)
    listview_api_delete = to_snake_case(SecretListApiDeleteView)
    listview_api_rename = to_snake_case(SecretListApiRenameView)


app_name = namespace

urlpatterns = [
    path("", SecretListView.as_view(), name=SecretReverseNames.listview),
    path("react-integration/api/listview/", SecretListApiView.as_view(), name=SecretReverseNames.listview_api_all),
    re_path(
        r"^react-integration/api/listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        SecretListApiView.as_view(),
        name=SecretReverseNames.listview_api,
    ),
    path(
        "react-integration/api/clone/<int:llm_client_id>/<str:new_name>/",
        SecretListApiCloneView.as_view(),
        name=SecretReverseNames.listview_api_clone,
    ),
    path(
        "react-integration/api/delete/<int:llm_client_id>/",
        SecretListApiDeleteView.as_view(),
        name=SecretReverseNames.listview_api_delete,
    ),
    path(
        "react-integration/api/rename/<int:llm_client_id>/<str:new_name>/",
        SecretListApiRenameView.as_view(),
        name=SecretReverseNames.listview_api_rename,
    ),
    path("secrets/<str:hashed_id>/", SecretDetailView.as_view(), name=SecretReverseNames.detailview),
]
