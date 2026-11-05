"""
Django URL patterns for the vectorsearch app's web console pages.

- ``/vectorsearch/``
- ``/vectorsearch/vectorsearchs/<hashed_id>/``

The Vectorsearch api is at ``/api/v1/vectorsearches/`` (:mod:`smarter.apps.vectorsearch.api.v1.urls`), and the
endpoints that the console's React apps call are at ``/api/web/vectorsearch/``
(:mod:`smarter.apps.vectorsearch.api.web.urls`).
"""

from django.urls import path

from smarter.apps.vectorsearch.views.detailview import VectorsearchDetailView
from smarter.apps.vectorsearch.views.listview.view import VectorsearchListView
from smarter.common.utils import to_snake_case

from .const import namespace

app_name = namespace


class VectorsearchReverseNames:
    """
    Reverse view names for the Vectorsearch app's console pages.

    The endpoints that the list page's React app calls are in the web console's api:
    see :class:`smarter.apps.vectorsearch.api.web.urls.VectorsearchApiWebReverseNames`.
    """

    namespace = namespace

    detailview = to_snake_case(VectorsearchDetailView.__name__)
    listview = to_snake_case(VectorsearchListView.__name__)


urlpatterns = [
    path("vectorsearchs/<str:hashed_id>/", VectorsearchDetailView.as_view(), name=VectorsearchReverseNames.detailview),
    path("", VectorsearchListView.as_view(), name=VectorsearchReverseNames.listview),
]
