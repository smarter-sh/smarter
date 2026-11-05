"""
URL configuration for the Vectorsearch app's endpoints in the web console's api.

These are mounted at ``/api/web/vectorsearch/``, and the Vectorsearch list page's React app calls
them. See :mod:`smarter.apps.api.web` and :mod:`smarter.apps.vectorsearch.views.listview.api`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path, re_path

from smarter.apps.api.web.const import path_namespace
from smarter.apps.vectorsearch.const import namespace
from smarter.apps.vectorsearch.views.listview.api import (
    VectorsearchListApiCloneView,
    VectorsearchListApiDeleteView,
    VectorsearchListApiRenameView,
    VectorsearchListApiView,
)
from smarter.common.utils import to_snake_case

app_name = namespace


class VectorsearchApiWebReverseNames:
    """
    Reverse view names for the Vectorsearch app's endpoints in the web console's api.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(VectorsearchApiWebReverseNames.namespace, VectorsearchApiWebReverseNames.listview_all)
    """

    namespace = f"{path_namespace}:{namespace}"

    listview = to_snake_case(VectorsearchListApiView.__name__)
    listview_all = to_snake_case(VectorsearchListApiView.__name__) + "_all"
    clone = to_snake_case(VectorsearchListApiCloneView.__name__)
    delete = to_snake_case(VectorsearchListApiDeleteView.__name__)
    rename = to_snake_case(VectorsearchListApiRenameView.__name__)


urlpatterns = [
    path("listview/", VectorsearchListApiView.as_view(), name=VectorsearchApiWebReverseNames.listview_all),
    re_path(
        r"^listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        VectorsearchListApiView.as_view(),
        name=VectorsearchApiWebReverseNames.listview,
    ),
    path(
        "clone/<int:vectorsearch_id>/<str:new_name>/",
        VectorsearchListApiCloneView.as_view(),
        name=VectorsearchApiWebReverseNames.clone,
    ),
    path(
        "delete/<int:vectorsearch_id>/",
        VectorsearchListApiDeleteView.as_view(),
        name=VectorsearchApiWebReverseNames.delete,
    ),
    path(
        "rename/<int:vectorsearch_id>/<str:new_name>/",
        VectorsearchListApiRenameView.as_view(),
        name=VectorsearchApiWebReverseNames.rename,
    ),
]
