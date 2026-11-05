"""URL configuration for the plugin app."""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.detailview import PluginDetailView
from .views.listview.view import PluginListView

app_name = namespace


class PluginReverseNames:
    """
    Reverse view names for the plugin app's console pages.

    The endpoints that the list page's React app calls are in the web console's api:
    see :class:`smarter.apps.llmtool.api.web.urls.PluginApiWebReverseNames`.
    """

    namespace = namespace

    listview = to_snake_case(PluginListView.__name__)
    detailview = to_snake_case(PluginDetailView.__name__)


urlpatterns = [
    path("", PluginListView.as_view(), name=PluginReverseNames.listview),
    path("plugins/<str:hashed_id>/", PluginDetailView.as_view(), name=PluginReverseNames.detailview),
]
