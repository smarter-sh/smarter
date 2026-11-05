"""
URL configuration for the LLMTool app's endpoints in the web console's api.

These are mounted at ``/api/web/llmtool/``. The LLMTools list page's React app calls the list,
clone, delete and rename endpoints, and ``listview/extensions/`` for its read-only Extensions tab.
The Extensions pages' React app calls the endpoints under ``extensions/``: see
:mod:`smarter.apps.llmtool.extension.api.web.urls`. See also :mod:`smarter.apps.api.web` and
:mod:`smarter.apps.llmtool.views.listview.api`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import include, path, re_path

from smarter.apps.api.web.const import path_namespace
from smarter.apps.llmtool.const import namespace
from smarter.apps.llmtool.extension.api.web import urls as extension_web_urls
from smarter.apps.llmtool.extension.urls import namespace as extension_namespace
from smarter.apps.llmtool.views.listview.api import (
    PluginListApiCloneView,
    PluginListApiDeleteView,
    PluginListApiExtensionsView,
    PluginListApiRenameView,
    PluginListApiView,
)
from smarter.common.utils import to_snake_case

app_name = namespace


class PluginApiWebReverseNames:
    """
    Reverse view names for the LLMTool app's endpoints in the web console's api.

    The Extensions pages' endpoints are in
    :class:`smarter.apps.llmtool.extension.api.web.urls.ExtensionApiWebReverseNames`.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(PluginApiWebReverseNames.namespace, PluginApiWebReverseNames.listview_all)
    """

    namespace = f"{path_namespace}:{namespace}"

    listview = to_snake_case(PluginListApiView.__name__)
    listview_all = to_snake_case(PluginListApiView.__name__) + "_all"
    listview_extensions = to_snake_case(PluginListApiExtensionsView.__name__)
    clone = to_snake_case(PluginListApiCloneView.__name__)
    delete = to_snake_case(PluginListApiDeleteView.__name__)
    rename = to_snake_case(PluginListApiRenameView.__name__)


urlpatterns = [
    path("listview/", PluginListApiView.as_view(), name=PluginApiWebReverseNames.listview_all),
    re_path(
        r"^listview/(?:(?P<ownership_filter>owned|shared|all)/)?$",
        PluginListApiView.as_view(),
        name=PluginApiWebReverseNames.listview,
    ),
    path(
        "listview/extensions/",
        PluginListApiExtensionsView.as_view(),
        name=PluginApiWebReverseNames.listview_extensions,
    ),
    path(
        "clone/<int:llmclient_id>/<str:new_name>/",
        PluginListApiCloneView.as_view(),
        name=PluginApiWebReverseNames.clone,
    ),
    path(
        "delete/<int:llmclient_id>/",
        PluginListApiDeleteView.as_view(),
        name=PluginApiWebReverseNames.delete,
    ),
    path(
        "rename/<int:llmclient_id>/<str:new_name>/",
        PluginListApiRenameView.as_view(),
        name=PluginApiWebReverseNames.rename,
    ),
    path("extensions/", include(extension_web_urls, namespace=extension_namespace)),
]
