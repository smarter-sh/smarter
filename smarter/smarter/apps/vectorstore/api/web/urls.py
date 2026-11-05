"""
URL configuration for the Vectorstore app's endpoints in the web console's api.

These are mounted at ``/api/web/vectorstore/``, and the Vectorstore list page's React app calls
them. See :mod:`smarter.apps.api.web` and :mod:`smarter.apps.vectorstore.views.listview.api`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path, re_path

from smarter.apps.api.web.const import path_namespace
from smarter.apps.vectorstore.const import namespace
from smarter.apps.vectorstore.views.listview.api import (
    VectorstoreListApiCloneView,
    VectorstoreListApiDeleteView,
    VectorstoreListApiRenameView,
    VectorstoreListApiView,
)
from smarter.common.utils import to_snake_case

app_name = namespace


class VectorstoreApiWebReverseNames:
    """
    Reverse view names for the Vectorstore app's endpoints in the web console's api.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(VectorstoreApiWebReverseNames.namespace, VectorstoreApiWebReverseNames.listview_all)
    """

    namespace = f"{path_namespace}:{namespace}"

    listview = to_snake_case(VectorstoreListApiView.__name__)
    listview_all = to_snake_case(VectorstoreListApiView.__name__) + "_all"
    clone = to_snake_case(VectorstoreListApiCloneView.__name__)
    delete = to_snake_case(VectorstoreListApiDeleteView.__name__)
    rename = to_snake_case(VectorstoreListApiRenameView.__name__)


urlpatterns = [
    path("listview/", VectorstoreListApiView.as_view(), name=VectorstoreApiWebReverseNames.listview_all),
    re_path(
        r"^listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        VectorstoreListApiView.as_view(),
        name=VectorstoreApiWebReverseNames.listview,
    ),
    path(
        "clone/<int:vectorstore_id>/<str:new_name>/",
        VectorstoreListApiCloneView.as_view(),
        name=VectorstoreApiWebReverseNames.clone,
    ),
    path(
        "delete/<int:vectorstore_id>/",
        VectorstoreListApiDeleteView.as_view(),
        name=VectorstoreApiWebReverseNames.delete,
    ),
    path(
        "rename/<int:vectorstore_id>/<str:new_name>/",
        VectorstoreListApiRenameView.as_view(),
        name=VectorstoreApiWebReverseNames.rename,
    ),
]
