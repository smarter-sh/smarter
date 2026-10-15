"""
URL patterns of the web console's Extensions pages and their api, for superusers only.

how we got here:
 - /extensions/
"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .views import (
    ExtensionAccountsApiView,
    ExtensionAvailabilityApiView,
    ExtensionCheckUpdatesApiView,
    ExtensionConfigureApiView,
    ExtensionDetailApiView,
    ExtensionDetailView,
    ExtensionDisableApiView,
    ExtensionEnableApiView,
    ExtensionInstallApiView,
    ExtensionListApiView,
    ExtensionListView,
    ExtensionRegistryApiView,
    ExtensionRollbackApiView,
    ExtensionUninstallApiView,
    ExtensionUpdateApiView,
    ExtensionUploadApiView,
)

namespace = "extension"
app_name = namespace

API = "react-integration/api/"
"""The prefix of the api's paths.

The React apps build each action's url from it.
"""


class ExtensionReverseNames:
    """Named URL patterns of the Extensions pages and their api."""

    namespace = namespace

    listview = to_snake_case(ExtensionListView.__name__)
    detailview = to_snake_case(ExtensionDetailView.__name__)
    api_root = "extension_api_root"
    api_list = to_snake_case(ExtensionListApiView.__name__)
    api_registry = to_snake_case(ExtensionRegistryApiView.__name__)
    api_check_updates = to_snake_case(ExtensionCheckUpdatesApiView.__name__)
    api_install = to_snake_case(ExtensionInstallApiView.__name__)
    api_upload = to_snake_case(ExtensionUploadApiView.__name__)
    api_accounts = to_snake_case(ExtensionAccountsApiView.__name__)
    api_detail = to_snake_case(ExtensionDetailApiView.__name__)
    api_enable = to_snake_case(ExtensionEnableApiView.__name__)
    api_disable = to_snake_case(ExtensionDisableApiView.__name__)
    api_update = to_snake_case(ExtensionUpdateApiView.__name__)
    api_rollback = to_snake_case(ExtensionRollbackApiView.__name__)
    api_configure = to_snake_case(ExtensionConfigureApiView.__name__)
    api_availability = to_snake_case(ExtensionAvailabilityApiView.__name__)
    api_uninstall = to_snake_case(ExtensionUninstallApiView.__name__)


urlpatterns = [
    path("", ExtensionListView.as_view(), name=ExtensionReverseNames.listview),
    path(API, ExtensionListApiView.as_view(), name=ExtensionReverseNames.api_root),
    path(f"{API}list/", ExtensionListApiView.as_view(), name=ExtensionReverseNames.api_list),
    path(f"{API}registry/", ExtensionRegistryApiView.as_view(), name=ExtensionReverseNames.api_registry),
    path(f"{API}check-updates/", ExtensionCheckUpdatesApiView.as_view(), name=ExtensionReverseNames.api_check_updates),
    path(f"{API}install/", ExtensionInstallApiView.as_view(), name=ExtensionReverseNames.api_install),
    path(f"{API}upload/", ExtensionUploadApiView.as_view(), name=ExtensionReverseNames.api_upload),
    path(f"{API}accounts/", ExtensionAccountsApiView.as_view(), name=ExtensionReverseNames.api_accounts),
    path(f"{API}extensions/<slug:slug>/", ExtensionDetailApiView.as_view(), name=ExtensionReverseNames.api_detail),
    path(
        f"{API}extensions/<slug:slug>/enable/", ExtensionEnableApiView.as_view(), name=ExtensionReverseNames.api_enable
    ),
    path(
        f"{API}extensions/<slug:slug>/disable/",
        ExtensionDisableApiView.as_view(),
        name=ExtensionReverseNames.api_disable,
    ),
    path(
        f"{API}extensions/<slug:slug>/update/", ExtensionUpdateApiView.as_view(), name=ExtensionReverseNames.api_update
    ),
    path(
        f"{API}extensions/<slug:slug>/rollback/",
        ExtensionRollbackApiView.as_view(),
        name=ExtensionReverseNames.api_rollback,
    ),
    path(
        f"{API}extensions/<slug:slug>/configure/",
        ExtensionConfigureApiView.as_view(),
        name=ExtensionReverseNames.api_configure,
    ),
    path(
        f"{API}extensions/<slug:slug>/availability/",
        ExtensionAvailabilityApiView.as_view(),
        name=ExtensionReverseNames.api_availability,
    ),
    path(
        f"{API}extensions/<slug:slug>/uninstall/",
        ExtensionUninstallApiView.as_view(),
        name=ExtensionReverseNames.api_uninstall,
    ),
    path("<slug:slug>/", ExtensionDetailView.as_view(), name=ExtensionReverseNames.detailview),
]
