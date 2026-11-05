"""
URL configuration for the Proxy app's endpoints in the web console's api.

These are mounted at ``/api/web/proxy/``, and the Proxy list page's React app calls
them. See :mod:`smarter.apps.api.web` and :mod:`smarter.apps.proxy.views.listview.api`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path, re_path

from smarter.apps.api.web.const import path_namespace
from smarter.apps.proxy.const import namespace
from smarter.apps.proxy.views.listview.api import (
    ProxyListApiCloneView,
    ProxyListApiDeleteView,
    ProxyListApiRenameView,
    ProxyListApiView,
)
from smarter.common.utils import to_snake_case

app_name = namespace


class ProxyApiWebReverseNames:
    """
    Reverse view names for the Proxy app's endpoints in the web console's api.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(ProxyApiWebReverseNames.namespace, ProxyApiWebReverseNames.listview_all)
    """

    namespace = f"{path_namespace}:{namespace}"

    listview = to_snake_case(ProxyListApiView.__name__)
    listview_all = to_snake_case(ProxyListApiView.__name__) + "_all"
    clone = to_snake_case(ProxyListApiCloneView.__name__)
    delete = to_snake_case(ProxyListApiDeleteView.__name__)
    rename = to_snake_case(ProxyListApiRenameView.__name__)


urlpatterns = [
    path("listview/", ProxyListApiView.as_view(), name=ProxyApiWebReverseNames.listview_all),
    re_path(
        r"^listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        ProxyListApiView.as_view(),
        name=ProxyApiWebReverseNames.listview,
    ),
    path(
        "clone/<int:proxy_id>/<str:new_name>/",
        ProxyListApiCloneView.as_view(),
        name=ProxyApiWebReverseNames.clone,
    ),
    path(
        "delete/<int:proxy_id>/",
        ProxyListApiDeleteView.as_view(),
        name=ProxyApiWebReverseNames.delete,
    ),
    path(
        "rename/<int:proxy_id>/<str:new_name>/",
        ProxyListApiRenameView.as_view(),
        name=ProxyApiWebReverseNames.rename,
    ),
]
