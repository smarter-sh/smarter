"""URL configuration for the plugin app."""

from django.urls import path

from smarter.common.utils import camel_case_object_name

from .const import namespace
from .views.plugin import PluginDetailView, PluginListView

app_name = namespace


class PluginReverseViews:
    """
    Reverse view names for the plugin app.
    """

    namespace = namespace
    listview = camel_case_object_name(PluginListView)
    detailview = camel_case_object_name(PluginDetailView)


urlpatterns = [
    path("plugins/", PluginListView.as_view(), name=PluginReverseViews.listview),
    path("plugins/<str:kind>/<str:name>/", PluginDetailView.as_view(), name=PluginReverseViews.detailview),
]
