"""URL configuration for the connection app."""

from django.urls import path

from smarter.common.utils import camel_case_object_name

from .const import namespace
from .views.connection import ConnectionDetailView, ConnectionListView

app_name = namespace


class ConnectionReverseViews:
    """
    Reverse view names for the connection app.
    """

    namespace = namespace
    listview = camel_case_object_name(ConnectionListView)
    detailview = camel_case_object_name(ConnectionDetailView)


urlpatterns = [
    path("connections/", ConnectionListView.as_view(), name=ConnectionReverseViews.listview),
    path("connections/<str:kind>/<str:name>/", ConnectionDetailView.as_view(), name=ConnectionReverseViews.detailview),
]
