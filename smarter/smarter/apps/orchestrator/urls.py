"""
Django URL patterns for the orchestrator app.

how we got here:
 - /orchestrators/api/v1/
"""

from django.urls import include, path, re_path

from smarter.apps.orchestrator.views.detailview import OrchestratorDetailView
from smarter.apps.orchestrator.views.listview.api import (
    OrchestratorListApiCloneView,
    OrchestratorListApiDeleteView,
    OrchestratorListApiRenameView,
    OrchestratorListApiView,
)
from smarter.apps.orchestrator.views.listview.view import OrchestratorListView
from smarter.common.utils import to_snake_case

from .api.const import namespace as api_namespace
from .const import namespace

app_name = namespace


class OrchestratorReverseNames:
    """
    Holds named URL patterns for the account dashboard.

    This class provides constants for all named URL patterns used in the account dashboard views.
    """

    namespace = namespace

    listview = to_snake_case(OrchestratorListApiView.__name__)
    detailview = to_snake_case(OrchestratorDetailView.__name__)

    listview = to_snake_case(OrchestratorListView.__name__)
    listview_api = to_snake_case(OrchestratorListApiView.__name__)
    listview_api_all = to_snake_case(OrchestratorListApiView.__name__) + "_all"
    listview_api_clone = to_snake_case(OrchestratorListApiCloneView.__name__)
    listview_api_delete = to_snake_case(OrchestratorListApiDeleteView.__name__)
    listview_api_rename = to_snake_case(OrchestratorListApiRenameView.__name__)


urlpatterns = [
    path("api/", include("smarter.apps.orchestrator.api.urls", namespace=api_namespace)),
    path("orchestrators/<str:hashed_id>/", OrchestratorDetailView.as_view(), name=OrchestratorReverseNames.detailview),
    path("", OrchestratorListView.as_view(), name=OrchestratorReverseNames.listview),
    path(
        "react-integration/api/listview/",
        OrchestratorListApiView.as_view(),
        name=OrchestratorReverseNames.listview_api_all,
    ),
    re_path(
        r"^react-integration/api/listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        OrchestratorListApiView.as_view(),
        name=OrchestratorReverseNames.listview_api,
    ),
    path(
        "react-integration/api/clone/<int:llmclient_id>/<str:new_name>/",
        OrchestratorListApiCloneView.as_view(),
        name=OrchestratorReverseNames.listview_api_clone,
    ),
    path(
        "react-integration/api/delete/<int:llmclient_id>/",
        OrchestratorListApiDeleteView.as_view(),
        name=OrchestratorReverseNames.listview_api_delete,
    ),
    path(
        "react-integration/api/rename/<int:llmclient_id>/<str:new_name>/",
        OrchestratorListApiRenameView.as_view(),
        name=OrchestratorReverseNames.listview_api_rename,
    ),
]
