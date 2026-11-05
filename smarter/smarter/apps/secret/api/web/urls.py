"""
URL configuration for the Secret app's endpoints in the web console's api.

These are mounted at ``/api/web/secret/``, and the Secret list page's React app calls
them. See :mod:`smarter.apps.api.web` and :mod:`smarter.apps.secret.views.listview.api`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path, re_path

from smarter.apps.api.web.const import path_namespace
from smarter.apps.secret.const import namespace
from smarter.apps.secret.views.listview.api import (
    SecretListApiCloneView,
    SecretListApiDeleteView,
    SecretListApiRenameView,
    SecretListApiView,
)
from smarter.common.utils import to_snake_case

app_name = namespace


class SecretApiWebReverseNames:
    """
    Reverse view names for the Secret app's endpoints in the web console's api.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(SecretApiWebReverseNames.namespace, SecretApiWebReverseNames.listview_all)
    """

    namespace = f"{path_namespace}:{namespace}"

    listview = to_snake_case(SecretListApiView.__name__)
    listview_all = to_snake_case(SecretListApiView.__name__) + "_all"
    clone = to_snake_case(SecretListApiCloneView.__name__)
    delete = to_snake_case(SecretListApiDeleteView.__name__)
    rename = to_snake_case(SecretListApiRenameView.__name__)


urlpatterns = [
    path("listview/", SecretListApiView.as_view(), name=SecretApiWebReverseNames.listview_all),
    re_path(
        r"^listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        SecretListApiView.as_view(),
        name=SecretApiWebReverseNames.listview,
    ),
    path(
        "clone/<int:secret_id>/<str:new_name>/",
        SecretListApiCloneView.as_view(),
        name=SecretApiWebReverseNames.clone,
    ),
    path(
        "delete/<int:secret_id>/",
        SecretListApiDeleteView.as_view(),
        name=SecretApiWebReverseNames.delete,
    ),
    path(
        "rename/<int:secret_id>/<str:new_name>/",
        SecretListApiRenameView.as_view(),
        name=SecretApiWebReverseNames.rename,
    ),
]
