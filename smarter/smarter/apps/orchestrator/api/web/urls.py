"""
URL configuration for the Orchestrator app's endpoints in the web console's api.

These are mounted at ``/api/web/orchestrator/``, and the Orchestrator list page's React app calls
them. See :mod:`smarter.apps.api.web` and :mod:`smarter.apps.orchestrator.views.listview.api`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path, re_path

from smarter.apps.api.web.const import path_namespace
from smarter.apps.orchestrator.const import namespace
from smarter.apps.orchestrator.views.listview.api import (
    OrchestratorListApiCloneView,
    OrchestratorListApiDeleteView,
    OrchestratorListApiRenameView,
    OrchestratorListApiView,
)
from smarter.common.utils import to_snake_case

app_name = namespace


class OrchestratorApiWebReverseNames:
    """
    Reverse view names for the Orchestrator app's endpoints in the web console's api.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(OrchestratorApiWebReverseNames.namespace, OrchestratorApiWebReverseNames.listview_all)
    """

    namespace = f"{path_namespace}:{namespace}"

    listview = to_snake_case(OrchestratorListApiView.__name__)
    listview_all = to_snake_case(OrchestratorListApiView.__name__) + "_all"
    clone = to_snake_case(OrchestratorListApiCloneView.__name__)
    delete = to_snake_case(OrchestratorListApiDeleteView.__name__)
    rename = to_snake_case(OrchestratorListApiRenameView.__name__)


urlpatterns = [
    path("listview/", OrchestratorListApiView.as_view(), name=OrchestratorApiWebReverseNames.listview_all),
    re_path(
        r"^listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        OrchestratorListApiView.as_view(),
        name=OrchestratorApiWebReverseNames.listview,
    ),
    path(
        "clone/<int:orchestrator_id>/<str:new_name>/",
        OrchestratorListApiCloneView.as_view(),
        name=OrchestratorApiWebReverseNames.clone,
    ),
    path(
        "delete/<int:orchestrator_id>/",
        OrchestratorListApiDeleteView.as_view(),
        name=OrchestratorApiWebReverseNames.delete,
    ),
    path(
        "rename/<int:orchestrator_id>/<str:new_name>/",
        OrchestratorListApiRenameView.as_view(),
        name=OrchestratorApiWebReverseNames.rename,
    ),
]
