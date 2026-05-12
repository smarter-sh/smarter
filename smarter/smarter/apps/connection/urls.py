"""URL configuration for the connection app."""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views.connection import ConnectionDetailView, ConnectionListView

app_name = namespace


class ConnectionReverseNames:
    """
    Reverse view names for the connection app.
    """

    namespace = namespace
    listview = to_snake_case(ConnectionListView)
    detailview = to_snake_case(ConnectionDetailView)


urlpatterns = [
    path("connections/", ConnectionListView.as_view(), name=ConnectionReverseNames.listview),
    path("connections/<str:kind>/<str:name>/", ConnectionDetailView.as_view(), name=ConnectionReverseNames.detailview),
]
