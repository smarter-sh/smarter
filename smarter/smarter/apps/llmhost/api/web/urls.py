"""
URL configuration for the LLMHost app's endpoints in the web console's api.

These are mounted at ``/api/web/llmhost/``, and the LLMHost list page's React app calls them. The
LLMHostCompute list page's React app calls the ones under ``/api/web/llmhost/compute/``. See
:mod:`smarter.apps.api.web` and :mod:`smarter.apps.llmhost.views.listview.api`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path, re_path

from smarter.apps.api.web.const import path_namespace
from smarter.apps.llmhost.const import namespace
from smarter.apps.llmhost.views.listview.api import (
    LLMHostComputeListApiCloneView,
    LLMHostComputeListApiDeleteView,
    LLMHostComputeListApiRenameView,
    LLMHostComputeListApiView,
    LLMHostListApiCloneView,
    LLMHostListApiDeleteView,
    LLMHostListApiRenameView,
    LLMHostListApiView,
)
from smarter.common.utils import to_snake_case

app_name = namespace


class LLMHostApiWebReverseNames:
    """
    Reverse view names for the LLMHost app's endpoints in the web console's api.

    The ``compute_`` names are the LLMHostCompute list page's endpoints.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(LLMHostApiWebReverseNames.namespace, LLMHostApiWebReverseNames.listview_all)
    """

    namespace = f"{path_namespace}:{namespace}"

    listview = to_snake_case(LLMHostListApiView.__name__)
    listview_all = to_snake_case(LLMHostListApiView.__name__) + "_all"
    clone = to_snake_case(LLMHostListApiCloneView.__name__)
    delete = to_snake_case(LLMHostListApiDeleteView.__name__)
    rename = to_snake_case(LLMHostListApiRenameView.__name__)

    compute_listview = to_snake_case(LLMHostComputeListApiView.__name__)
    compute_listview_all = to_snake_case(LLMHostComputeListApiView.__name__) + "_all"
    compute_clone = to_snake_case(LLMHostComputeListApiCloneView.__name__)
    compute_delete = to_snake_case(LLMHostComputeListApiDeleteView.__name__)
    compute_rename = to_snake_case(LLMHostComputeListApiRenameView.__name__)


urlpatterns = [
    path("listview/", LLMHostListApiView.as_view(), name=LLMHostApiWebReverseNames.listview_all),
    re_path(
        r"^listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        LLMHostListApiView.as_view(),
        name=LLMHostApiWebReverseNames.listview,
    ),
    path(
        "clone/<int:llmhost_id>/<str:new_name>/",
        LLMHostListApiCloneView.as_view(),
        name=LLMHostApiWebReverseNames.clone,
    ),
    path(
        "delete/<int:llmhost_id>/",
        LLMHostListApiDeleteView.as_view(),
        name=LLMHostApiWebReverseNames.delete,
    ),
    path(
        "rename/<int:llmhost_id>/<str:new_name>/",
        LLMHostListApiRenameView.as_view(),
        name=LLMHostApiWebReverseNames.rename,
    ),
    # LLMHostCompute
    path(
        "compute/listview/",
        LLMHostComputeListApiView.as_view(),
        name=LLMHostApiWebReverseNames.compute_listview_all,
    ),
    re_path(
        r"^compute/listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        LLMHostComputeListApiView.as_view(),
        name=LLMHostApiWebReverseNames.compute_listview,
    ),
    path(
        "compute/clone/<int:llmhost_compute_id>/<str:new_name>/",
        LLMHostComputeListApiCloneView.as_view(),
        name=LLMHostApiWebReverseNames.compute_clone,
    ),
    path(
        "compute/delete/<int:llmhost_compute_id>/",
        LLMHostComputeListApiDeleteView.as_view(),
        name=LLMHostApiWebReverseNames.compute_delete,
    ),
    path(
        "compute/rename/<int:llmhost_compute_id>/<str:new_name>/",
        LLMHostComputeListApiRenameView.as_view(),
        name=LLMHostApiWebReverseNames.compute_rename,
    ),
]
