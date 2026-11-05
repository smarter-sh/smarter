"""
URL configuration for the API key (AuthToken) endpoints in the web console's api.

These are mounted at ``/api/web/authtoken/``, and the API key list page's React app calls
them. See :mod:`smarter.apps.api.web` and :mod:`smarter.lib.drf.views.listview.api`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path, re_path

from smarter.apps.api.web.const import path_namespace
from smarter.common.utils import to_snake_case
from smarter.lib.drf.const import namespace
from smarter.lib.drf.views.listview.api import (
    AuthTokenListApiCloneView,
    AuthTokenListApiDeleteView,
    AuthTokenListApiRenameView,
    AuthTokenListApiView,
)

app_name = namespace


class AuthTokenApiWebReverseNames:
    """
    Reverse view names for the API key (AuthToken) endpoints in the web console's api.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(AuthTokenApiWebReverseNames.namespace, AuthTokenApiWebReverseNames.listview_all)
    """

    namespace = f"{path_namespace}:{namespace}"

    listview = to_snake_case(AuthTokenListApiView.__name__)
    listview_all = to_snake_case(AuthTokenListApiView.__name__) + "_all"
    clone = to_snake_case(AuthTokenListApiCloneView.__name__)
    delete = to_snake_case(AuthTokenListApiDeleteView.__name__)
    rename = to_snake_case(AuthTokenListApiRenameView.__name__)


urlpatterns = [
    path("listview/", AuthTokenListApiView.as_view(), name=AuthTokenApiWebReverseNames.listview_all),
    re_path(
        r"^listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        AuthTokenListApiView.as_view(),
        name=AuthTokenApiWebReverseNames.listview,
    ),
    path(
        "clone/<uuid:authtoken_id>/<str:new_name>/",
        AuthTokenListApiCloneView.as_view(),
        name=AuthTokenApiWebReverseNames.clone,
    ),
    path(
        "delete/<uuid:authtoken_id>/",
        AuthTokenListApiDeleteView.as_view(),
        name=AuthTokenApiWebReverseNames.delete,
    ),
    path(
        "rename/<uuid:authtoken_id>/<str:new_name>/",
        AuthTokenListApiRenameView.as_view(),
        name=AuthTokenApiWebReverseNames.rename,
    ),
]
