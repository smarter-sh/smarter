"""
URL configuration for the proxy app's web console pages.

These are mounted at ``/proxy/``. The Proxy passthrough itself is at ``/api/v1/proxy/``: see
:mod:`smarter.apps.proxy.api.v1.urls`.
"""

from django.urls import path

from smarter.apps.proxy.views.detailview import ProxyDetailView
from smarter.apps.proxy.views.listview.view import ProxyListView
from smarter.common.utils.conversion import to_snake_case

from .const import namespace

app_name = namespace


class ProxyReverseNames:
    """
    Reverse view names for the Proxy app's console pages.

    The endpoints that the list page's React app calls are in the web console's api:
    see :class:`smarter.apps.proxy.api.web.urls.ProxyApiWebReverseNames`.
    """

    namespace = namespace

    detailview = to_snake_case(ProxyDetailView.__name__)

    listview = to_snake_case(ProxyListView.__name__)


urlpatterns = [
    path("", ProxyListView.as_view(), name=ProxyReverseNames.listview),
    path("proxies/<str:hashed_id>/", ProxyDetailView.as_view(), name=ProxyReverseNames.detailview),
]
