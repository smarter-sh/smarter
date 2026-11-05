"""
URL configuration of the web console's API key (AuthToken) pages.

The endpoints that the list page's React app calls are in the web console's api: see
:mod:`smarter.lib.drf.api.web.urls`.
"""

from django.urls import path

from smarter.common.utils import to_snake_case
from smarter.lib.drf.views.detailview import AuthTokenDetailView
from smarter.lib.drf.views.listview.view import AuthTokenListView

from .const import namespace


class AuthTokenReverseNames:
    """
    Holds the names of the API key url patterns, for ``reverse()``.

    Each name is ``to_snake_case()`` of its view class's name. The endpoints that the list page's
    React app calls are in :class:`smarter.lib.drf.api.web.urls.AuthTokenApiWebReverseNames`.
    """

    namespace = namespace

    detailview = to_snake_case(AuthTokenDetailView.__name__)

    listview = to_snake_case(AuthTokenListView.__name__)


app_name = namespace

urlpatterns = [
    path("", AuthTokenListView.as_view(), name=AuthTokenReverseNames.listview),
    path("<uuid:authtoken_id>/", AuthTokenDetailView.as_view(), name=AuthTokenReverseNames.detailview),
]
