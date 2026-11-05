"""URL configuration for vectorstore app."""

from django.urls import path

from smarter.apps.vectorstore.views.detailview import VectorstoreDetailView
from smarter.apps.vectorstore.views.listview.view import VectorstoreListView
from smarter.common.utils.conversion import to_snake_case

from .const import namespace

app_name = namespace


class VectorstoreReverseNames:
    """
    Reverse view names for the Vectorstore app's console pages.

    The endpoints that the list page's React app calls are in the web console's api:
    see :class:`smarter.apps.vectorstore.api.web.urls.VectorstoreApiWebReverseNames`.
    """

    namespace = namespace

    detailview = to_snake_case(VectorstoreDetailView.__name__)

    listview = to_snake_case(VectorstoreListView.__name__)


urlpatterns = [
    path("", VectorstoreListView.as_view(), name=VectorstoreReverseNames.listview),
    path("vectors/<str:hashed_id>/", VectorstoreDetailView.as_view(), name=VectorstoreReverseNames.detailview),
]
