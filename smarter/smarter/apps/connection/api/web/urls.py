"""
URL configuration for the Connection app's endpoints in the web console's api.

These are mounted at ``/api/web/connection/``, and the Connection list page's React app calls
them. See :mod:`smarter.apps.api.web` and :mod:`smarter.apps.connection.views.listview.api`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path, re_path

from smarter.apps.api.web.const import path_namespace
from smarter.apps.connection.const import namespace
from smarter.apps.connection.views.listview.api import (
    ConnectionListApiCloneView,
    ConnectionListApiDeleteView,
    ConnectionListApiRenameView,
    ConnectionListApiView,
)
from smarter.common.utils import to_snake_case

app_name = namespace


class ConnectionApiWebReverseNames:
    """
    Reverse view names for the Connection app's endpoints in the web console's api.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(ConnectionApiWebReverseNames.namespace, ConnectionApiWebReverseNames.listview_all)
    """

    namespace = f"{path_namespace}:{namespace}"

    listview = to_snake_case(ConnectionListApiView.__name__)
    listview_all = to_snake_case(ConnectionListApiView.__name__) + "_all"
    clone = to_snake_case(ConnectionListApiCloneView.__name__)
    delete = to_snake_case(ConnectionListApiDeleteView.__name__)
    rename = to_snake_case(ConnectionListApiRenameView.__name__)


urlpatterns = [
    path("listview/", ConnectionListApiView.as_view(), name=ConnectionApiWebReverseNames.listview_all),
    re_path(
        r"^listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        ConnectionListApiView.as_view(),
        name=ConnectionApiWebReverseNames.listview,
    ),
    path(
        "clone/<int:connection_id>/<str:new_name>/",
        ConnectionListApiCloneView.as_view(),
        name=ConnectionApiWebReverseNames.clone,
    ),
    path(
        "delete/<int:connection_id>/",
        ConnectionListApiDeleteView.as_view(),
        name=ConnectionApiWebReverseNames.delete,
    ),
    path(
        "rename/<int:connection_id>/<str:new_name>/",
        ConnectionListApiRenameView.as_view(),
        name=ConnectionApiWebReverseNames.rename,
    ),
]
