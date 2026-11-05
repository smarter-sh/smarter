"""
Django URL patterns for the orchestrator app's web console pages.

- ``/orchestrator/``
- ``/orchestrator/orchestrators/<hashed_id>/``

The Orchestrator api is at ``/api/v1/orchestrators/`` (:mod:`smarter.apps.orchestrator.api.v1.urls`), and the
endpoints that the console's React apps call are at ``/api/web/orchestrator/``
(:mod:`smarter.apps.orchestrator.api.web.urls`).
"""

from django.urls import path

from smarter.apps.orchestrator.views.detailview import OrchestratorDetailView
from smarter.apps.orchestrator.views.listview.view import OrchestratorListView
from smarter.common.utils import to_snake_case

from .const import namespace

app_name = namespace


class OrchestratorReverseNames:
    """
    Reverse view names for the Orchestrator app's console pages.

    The endpoints that the list page's React app calls are in the web console's api:
    see :class:`smarter.apps.orchestrator.api.web.urls.OrchestratorApiWebReverseNames`.
    """

    namespace = namespace

    detailview = to_snake_case(OrchestratorDetailView.__name__)
    listview = to_snake_case(OrchestratorListView.__name__)


urlpatterns = [
    path("orchestrators/<str:hashed_id>/", OrchestratorDetailView.as_view(), name=OrchestratorReverseNames.detailview),
    path("", OrchestratorListView.as_view(), name=OrchestratorReverseNames.listview),
]
