"""
Django URL patterns for the chatapp

how we got here:
 - /providers/api/v1/

"""

from django.urls import include, path, re_path

from smarter.apps.provider.views.detailview import ProviderDetailView
from smarter.apps.provider.views.listview.api import (
    ProviderListApiCloneView,
    ProviderListApiDeleteView,
    ProviderListApiRenameView,
    ProviderListApiView,
)
from smarter.apps.provider.views.listview.view import ProviderListView
from smarter.common.utils import to_snake_case

from .api.const import namespace as api_namespace
from .const import namespace

app_name = namespace


class ProviderReverseNames:
    """
    Holds named URL patterns for the account dashboard.
    This class provides constants for all named URL patterns used in the account dashboard views.

    """

    namespace = namespace

    listview = to_snake_case(ProviderListApiView)
    detailview = to_snake_case(ProviderDetailView)

    listview = to_snake_case(ProviderListView)
    listview_api = to_snake_case(ProviderListApiView)
    listview_api_all = to_snake_case(ProviderListApiView) + "_all"
    listview_api_clone = to_snake_case(ProviderListApiCloneView)
    listview_api_delete = to_snake_case(ProviderListApiDeleteView)
    listview_api_rename = to_snake_case(ProviderListApiRenameView)


urlpatterns = [
    path("api/", include("smarter.apps.provider.api.urls", namespace=api_namespace)),
    path("providers/<int:provider_id>/", ProviderDetailView.as_view(), name=ProviderReverseNames.detailview),
    path("providers/<str:name>/", ProviderDetailView.as_view(), name="provider_by_name"),
    path("", ProviderListView.as_view(), name=ProviderReverseNames.listview),
    path("react-integration/api/listview/", ProviderListApiView.as_view(), name=ProviderReverseNames.listview_api_all),
    re_path(
        r"^react-integration/api/listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        ProviderListApiView.as_view(),
        name=ProviderReverseNames.listview_api,
    ),
    path(
        "react-integration/api/clone/<int:chatbot_id>/<str:new_name>/",
        ProviderListApiCloneView.as_view(),
        name=ProviderReverseNames.listview_api_clone,
    ),
    path(
        "react-integration/api/delete/<int:chatbot_id>/",
        ProviderListApiDeleteView.as_view(),
        name=ProviderReverseNames.listview_api_delete,
    ),
    path(
        "react-integration/api/rename/<int:chatbot_id>/<str:new_name>/",
        ProviderListApiRenameView.as_view(),
        name=ProviderReverseNames.listview_api_rename,
    ),
]
