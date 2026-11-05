"""
URL configuration for the MCPClient app's endpoints in the web console's api.

These are mounted at ``/api/web/mcpclient/``, and the MCPClient list page's React app calls
them. See :mod:`smarter.apps.api.web` and :mod:`smarter.apps.mcpclient.views.listview.api`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path, re_path

from smarter.apps.api.web.const import path_namespace
from smarter.apps.mcpclient.const import namespace
from smarter.apps.mcpclient.views.listview.api import (
    MCPClientListApiCloneView,
    MCPClientListApiDeleteView,
    MCPClientListApiRenameView,
    MCPClientListApiView,
)
from smarter.common.utils import to_snake_case

app_name = namespace


class MCPClientApiWebReverseNames:
    """
    Reverse view names for the MCPClient app's endpoints in the web console's api.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(MCPClientApiWebReverseNames.namespace, MCPClientApiWebReverseNames.listview_all)
    """

    namespace = f"{path_namespace}:{namespace}"

    listview = to_snake_case(MCPClientListApiView.__name__)
    listview_all = to_snake_case(MCPClientListApiView.__name__) + "_all"
    clone = to_snake_case(MCPClientListApiCloneView.__name__)
    delete = to_snake_case(MCPClientListApiDeleteView.__name__)
    rename = to_snake_case(MCPClientListApiRenameView.__name__)


urlpatterns = [
    path("listview/", MCPClientListApiView.as_view(), name=MCPClientApiWebReverseNames.listview_all),
    re_path(
        r"^listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        MCPClientListApiView.as_view(),
        name=MCPClientApiWebReverseNames.listview,
    ),
    path(
        "clone/<int:mcpclient_id>/<str:new_name>/",
        MCPClientListApiCloneView.as_view(),
        name=MCPClientApiWebReverseNames.clone,
    ),
    path(
        "delete/<int:mcpclient_id>/",
        MCPClientListApiDeleteView.as_view(),
        name=MCPClientApiWebReverseNames.delete,
    ),
    path(
        "rename/<int:mcpclient_id>/<str:new_name>/",
        MCPClientListApiRenameView.as_view(),
        name=MCPClientApiWebReverseNames.rename,
    ),
]
