"""
Django URL patterns for the vectorsearch app.

how we got here:
 - /vectorsearchs/api/v1/
"""

from django.urls import include, path, re_path

from smarter.apps.vectorsearch.views.detailview import VectorsearchDetailView
from smarter.apps.vectorsearch.views.listview.api import (
    VectorsearchListApiCloneView,
    VectorsearchListApiDeleteView,
    VectorsearchListApiRenameView,
    VectorsearchListApiView,
)
from smarter.apps.vectorsearch.views.listview.view import VectorsearchListView
from smarter.common.utils import to_snake_case

from .api.const import namespace as api_namespace
from .const import namespace

app_name = namespace


class VectorsearchReverseNames:
    """
    Holds named URL patterns for the account dashboard.

    This class provides constants for all named URL patterns used in the account dashboard views.
    """

    namespace = namespace

    listview = to_snake_case(VectorsearchListApiView.__name__)
    detailview = to_snake_case(VectorsearchDetailView.__name__)

    listview = to_snake_case(VectorsearchListView.__name__)
    listview_api = to_snake_case(VectorsearchListApiView.__name__)
    listview_api_all = to_snake_case(VectorsearchListApiView.__name__) + "_all"
    listview_api_clone = to_snake_case(VectorsearchListApiCloneView.__name__)
    listview_api_delete = to_snake_case(VectorsearchListApiDeleteView.__name__)
    listview_api_rename = to_snake_case(VectorsearchListApiRenameView.__name__)


urlpatterns = [
    path("api/", include("smarter.apps.vectorsearch.api.urls", namespace=api_namespace)),
    path("vectorsearchs/<str:hashed_id>/", VectorsearchDetailView.as_view(), name=VectorsearchReverseNames.detailview),
    path("", VectorsearchListView.as_view(), name=VectorsearchReverseNames.listview),
    path(
        "react-integration/api/listview/",
        VectorsearchListApiView.as_view(),
        name=VectorsearchReverseNames.listview_api_all,
    ),
    re_path(
        r"^react-integration/api/listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        VectorsearchListApiView.as_view(),
        name=VectorsearchReverseNames.listview_api,
    ),
    path(
        "react-integration/api/clone/<int:llm_client_id>/<str:new_name>/",
        VectorsearchListApiCloneView.as_view(),
        name=VectorsearchReverseNames.listview_api_clone,
    ),
    path(
        "react-integration/api/delete/<int:llm_client_id>/",
        VectorsearchListApiDeleteView.as_view(),
        name=VectorsearchReverseNames.listview_api_delete,
    ),
    path(
        "react-integration/api/rename/<int:llm_client_id>/<str:new_name>/",
        VectorsearchListApiRenameView.as_view(),
        name=VectorsearchReverseNames.listview_api_rename,
    ),
]
