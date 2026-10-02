"""
Django URL patterns for the llmhost app.

how we got here:
 - /llmhosts/api/v1/
"""

from django.urls import include, path, re_path

from smarter.apps.llmhost.views.detailview import (
    LLMHostComputeDetailView,
    LLMHostDetailView,
)
from smarter.apps.llmhost.views.listview.api import (
    LLMHostComputeListApiCloneView,
    LLMHostComputeListApiDeleteView,
    LLMHostComputeListApiRenameView,
    LLMHostComputeListApiView,
    LLMHostListApiCloneView,
    LLMHostListApiDeleteView,
    LLMHostListApiRenameView,
    LLMHostListApiView,
)
from smarter.apps.llmhost.views.listview.view import (
    LLMHostComputeListView,
    LLMHostListView,
)
from smarter.common.utils import to_snake_case

from .api.const import namespace as api_namespace
from .const import namespace

app_name = namespace


class LLMHostReverseNames:
    """
    Holds named URL patterns for the account dashboard.

    This class provides constants for all named URL patterns used in the account dashboard views.
    """

    namespace = namespace

    listview = to_snake_case(LLMHostListApiView.__name__)
    detailview = to_snake_case(LLMHostDetailView.__name__)

    listview = to_snake_case(LLMHostListView.__name__)
    listview_api = to_snake_case(LLMHostListApiView.__name__)
    listview_api_all = to_snake_case(LLMHostListApiView.__name__) + "_all"
    listview_api_clone = to_snake_case(LLMHostListApiCloneView.__name__)
    listview_api_delete = to_snake_case(LLMHostListApiDeleteView.__name__)
    listview_api_rename = to_snake_case(LLMHostListApiRenameView.__name__)

    compute_detailview = to_snake_case(LLMHostComputeDetailView.__name__)
    compute_listview = to_snake_case(LLMHostComputeListView.__name__)
    compute_listview_api = to_snake_case(LLMHostComputeListApiView.__name__)
    compute_listview_api_all = to_snake_case(LLMHostComputeListApiView.__name__) + "_all"
    compute_listview_api_clone = to_snake_case(LLMHostComputeListApiCloneView.__name__)
    compute_listview_api_delete = to_snake_case(LLMHostComputeListApiDeleteView.__name__)
    compute_listview_api_rename = to_snake_case(LLMHostComputeListApiRenameView.__name__)


urlpatterns = [
    path("api/", include("smarter.apps.llmhost.api.urls", namespace=api_namespace)),
    path("llmhosts/<str:hashed_id>/", LLMHostDetailView.as_view(), name=LLMHostReverseNames.detailview),
    path("", LLMHostListView.as_view(), name=LLMHostReverseNames.listview),
    path("react-integration/api/listview/", LLMHostListApiView.as_view(), name=LLMHostReverseNames.listview_api_all),
    re_path(
        r"^react-integration/api/listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        LLMHostListApiView.as_view(),
        name=LLMHostReverseNames.listview_api,
    ),
    path(
        "react-integration/api/clone/<int:llmhost_id>/<str:new_name>/",
        LLMHostListApiCloneView.as_view(),
        name=LLMHostReverseNames.listview_api_clone,
    ),
    path(
        "react-integration/api/delete/<int:llmhost_id>/",
        LLMHostListApiDeleteView.as_view(),
        name=LLMHostReverseNames.listview_api_delete,
    ),
    path(
        "react-integration/api/rename/<int:llmhost_id>/<str:new_name>/",
        LLMHostListApiRenameView.as_view(),
        name=LLMHostReverseNames.listview_api_rename,
    ),
    # LLMHostCompute
    path(
        "compute/react-integration/api/listview/",
        LLMHostComputeListApiView.as_view(),
        name=LLMHostReverseNames.compute_listview_api_all,
    ),
    re_path(
        r"^compute/react-integration/api/listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        LLMHostComputeListApiView.as_view(),
        name=LLMHostReverseNames.compute_listview_api,
    ),
    path(
        "compute/react-integration/api/clone/<int:llmhost_compute_id>/<str:new_name>/",
        LLMHostComputeListApiCloneView.as_view(),
        name=LLMHostReverseNames.compute_listview_api_clone,
    ),
    path(
        "compute/react-integration/api/delete/<int:llmhost_compute_id>/",
        LLMHostComputeListApiDeleteView.as_view(),
        name=LLMHostReverseNames.compute_listview_api_delete,
    ),
    path(
        "compute/react-integration/api/rename/<int:llmhost_compute_id>/<str:new_name>/",
        LLMHostComputeListApiRenameView.as_view(),
        name=LLMHostReverseNames.compute_listview_api_rename,
    ),
    path("compute/", LLMHostComputeListView.as_view(), name=LLMHostReverseNames.compute_listview),
    path(
        "compute/<str:hashed_id>/",
        LLMHostComputeDetailView.as_view(),
        name=LLMHostReverseNames.compute_detailview,
    ),
]
