"""URL configuration for vectorstore app."""

from django.urls import path, re_path

from smarter.apps.vectorstore.views.detailview import VectorstoreDetailView
from smarter.apps.vectorstore.views.listview.api import (
    VectorstoreListApiCloneView,
    VectorstoreListApiDeleteView,
    VectorstoreListApiRenameView,
    VectorstoreListApiView,
)
from smarter.apps.vectorstore.views.listview.view import VectorstoreListView
from smarter.common.utils.conversion import to_snake_case

from .const import namespace

app_name = namespace


class VectorstoreReverseNames:
    """
    Holds named URL patterns for the vectorstore app.

    This class provides constants for all named URL patterns used in the vectorstore app views.
    """

    namespace = namespace

    detailview = to_snake_case(VectorstoreDetailView.__name__)

    listview = to_snake_case(VectorstoreListView.__name__)
    listview_api = to_snake_case(VectorstoreListApiView.__name__)
    listview_api_all = to_snake_case(VectorstoreListApiView.__name__) + "_all"
    listview_api_clone = to_snake_case(VectorstoreListApiCloneView.__name__)
    listview_api_delete = to_snake_case(VectorstoreListApiDeleteView.__name__)
    listview_api_rename = to_snake_case(VectorstoreListApiRenameView.__name__)


urlpatterns = [
    path("", VectorstoreListView.as_view(), name=VectorstoreReverseNames.listview),
    path(
        "react-integration/api/listview/",
        VectorstoreListApiView.as_view(),
        name=VectorstoreReverseNames.listview_api_all,
    ),
    re_path(
        r"^react-integration/api/listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        VectorstoreListApiView.as_view(),
        name=VectorstoreReverseNames.listview_api,
    ),
    path(
        "react-integration/api/clone/<int:vectorstore_id>/<str:new_name>/",
        VectorstoreListApiCloneView.as_view(),
        name=VectorstoreReverseNames.listview_api_clone,
    ),
    path(
        "react-integration/api/delete/<int:vectorstore_id>/",
        VectorstoreListApiDeleteView.as_view(),
        name=VectorstoreReverseNames.listview_api_delete,
    ),
    path(
        "react-integration/api/rename/<int:vectorstore_id>/<str:new_name>/",
        VectorstoreListApiRenameView.as_view(),
        name=VectorstoreReverseNames.listview_api_rename,
    ),
    path("vectors/<str:hashed_id>/", VectorstoreDetailView.as_view(), name=VectorstoreReverseNames.detailview),
]
