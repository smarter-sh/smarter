"""URL configuration for the connection app."""

from django.urls import path

from smarter.apps.connection.views.detailview import (
    ApiConnectionDetailView,
    SqlConnectionDetailView,
)
from smarter.apps.connection.views.listview.view import ConnectionListView
from smarter.common.utils import to_snake_case

from .const import namespace

app_name = namespace


class ConnectionReverseNames:
    """
    Reverse view names for the connection app's console pages.

    The endpoints that the list page's React app calls are in the web console's api:
    see :class:`smarter.apps.connection.api.web.urls.ConnectionApiWebReverseNames`.
    """

    namespace = namespace

    sql_detailview = to_snake_case(SqlConnectionDetailView.__name__)
    api_detailview = to_snake_case(ApiConnectionDetailView.__name__)
    listview = to_snake_case(ConnectionListView.__name__)


urlpatterns = [
    path("", ConnectionListView.as_view(), name=ConnectionReverseNames.listview),
    path(
        "connections/sql-connection/<str:hashed_id>/",
        SqlConnectionDetailView.as_view(),
        name=ConnectionReverseNames.sql_detailview,
    ),
    path(
        "connections/api-connection/<str:hashed_id>/",
        ApiConnectionDetailView.as_view(),
        name=ConnectionReverseNames.api_detailview,
    ),
]
