"""
URL configuration for the Extensions pages' endpoints in the web console's api.

These are mounted at ``/api/web/llmtool/extensions/``, from
:mod:`smarter.apps.llmtool.api.web.urls`, and the Extensions pages' React app,
``@smarter/extension-console``, calls them. The page gives the app the api's root,
``/api/web/llmtool/extensions/``, and the app builds each endpoint's url from it, e.g.
``list/`` or ``<slug>/enable/``. See :mod:`smarter.apps.api.web` and
:mod:`smarter.apps.llmtool.extension.views`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path

from smarter.apps.api.web.const import path_namespace
from smarter.apps.llmtool.const import namespace as llmtool_namespace
from smarter.apps.llmtool.extension.urls import namespace
from smarter.apps.llmtool.extension.views import (
    ExtensionAccountsApiView,
    ExtensionAvailabilityApiView,
    ExtensionCheckUpdatesApiView,
    ExtensionConfigureApiView,
    ExtensionDetailApiView,
    ExtensionDisableApiView,
    ExtensionEnableApiView,
    ExtensionInstallApiView,
    ExtensionListApiView,
    ExtensionRegistryApiView,
    ExtensionRollbackApiView,
    ExtensionUninstallApiView,
    ExtensionUpdateApiView,
    ExtensionUploadApiView,
)
from smarter.common.utils import to_snake_case

app_name = namespace


class ExtensionApiWebReverseNames:
    """
    Reverse view names for the Extensions pages' endpoints in the web console's api.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(ExtensionApiWebReverseNames.namespace, ExtensionApiWebReverseNames.root)
    """

    namespace = f"{path_namespace}:{llmtool_namespace}:{namespace}"

    root = to_snake_case(ExtensionListApiView.__name__) + "_root"
    list = to_snake_case(ExtensionListApiView.__name__)
    registry = to_snake_case(ExtensionRegistryApiView.__name__)
    check_updates = to_snake_case(ExtensionCheckUpdatesApiView.__name__)
    install = to_snake_case(ExtensionInstallApiView.__name__)
    upload = to_snake_case(ExtensionUploadApiView.__name__)
    accounts = to_snake_case(ExtensionAccountsApiView.__name__)
    detail = to_snake_case(ExtensionDetailApiView.__name__)
    enable = to_snake_case(ExtensionEnableApiView.__name__)
    disable = to_snake_case(ExtensionDisableApiView.__name__)
    update = to_snake_case(ExtensionUpdateApiView.__name__)
    rollback = to_snake_case(ExtensionRollbackApiView.__name__)
    configure = to_snake_case(ExtensionConfigureApiView.__name__)
    availability = to_snake_case(ExtensionAvailabilityApiView.__name__)
    uninstall = to_snake_case(ExtensionUninstallApiView.__name__)


urlpatterns = [
    path("", ExtensionListApiView.as_view(), name=ExtensionApiWebReverseNames.root),
    path("list/", ExtensionListApiView.as_view(), name=ExtensionApiWebReverseNames.list),
    path("registry/", ExtensionRegistryApiView.as_view(), name=ExtensionApiWebReverseNames.registry),
    path("check-updates/", ExtensionCheckUpdatesApiView.as_view(), name=ExtensionApiWebReverseNames.check_updates),
    path("install/", ExtensionInstallApiView.as_view(), name=ExtensionApiWebReverseNames.install),
    path("upload/", ExtensionUploadApiView.as_view(), name=ExtensionApiWebReverseNames.upload),
    path("accounts/", ExtensionAccountsApiView.as_view(), name=ExtensionApiWebReverseNames.accounts),
    path("<slug:slug>/", ExtensionDetailApiView.as_view(), name=ExtensionApiWebReverseNames.detail),
    path(
        "<slug:slug>/enable/",
        ExtensionEnableApiView.as_view(),
        name=ExtensionApiWebReverseNames.enable,
    ),
    path(
        "<slug:slug>/disable/",
        ExtensionDisableApiView.as_view(),
        name=ExtensionApiWebReverseNames.disable,
    ),
    path(
        "<slug:slug>/update/",
        ExtensionUpdateApiView.as_view(),
        name=ExtensionApiWebReverseNames.update,
    ),
    path(
        "<slug:slug>/rollback/",
        ExtensionRollbackApiView.as_view(),
        name=ExtensionApiWebReverseNames.rollback,
    ),
    path(
        "<slug:slug>/configure/",
        ExtensionConfigureApiView.as_view(),
        name=ExtensionApiWebReverseNames.configure,
    ),
    path(
        "<slug:slug>/availability/",
        ExtensionAvailabilityApiView.as_view(),
        name=ExtensionApiWebReverseNames.availability,
    ),
    path(
        "<slug:slug>/uninstall/",
        ExtensionUninstallApiView.as_view(),
        name=ExtensionApiWebReverseNames.uninstall,
    ),
]
