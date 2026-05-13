"""URL configuration for the plugin app."""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.plugin import PluginDetailView, PluginListView

app_name = namespace


class PluginReverseNames:
    """
    Reverse view names for the plugin app.
    """

    namespace = namespace
    listview = to_snake_case(PluginListView)
    detailview = to_snake_case(PluginDetailView)


urlpatterns = [
    path("plugins/", PluginListView.as_view(), name=PluginReverseNames.listview),
    path("plugins/<str:kind>/<str:name>/", PluginDetailView.as_view(), name=PluginReverseNames.detailview),
]
