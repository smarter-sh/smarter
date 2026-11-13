"""
URL configuration of the Extensions REST api.

These are mounted at ``/api/v1/extensions/``. See :mod:`smarter.apps.llmtool.extension.api.v1.views`.
The fixed paths come before ``<slug>/``, which would match them.
"""

from django.urls import path

from smarter.apps.llmtool.extension.urls import namespace
from smarter.common.utils import to_snake_case

from .views import (
    ExtensionV1AvailabilityView,
    ExtensionV1CheckUpdatesView,
    ExtensionV1ConfigureView,
    ExtensionV1DetailView,
    ExtensionV1DisableView,
    ExtensionV1EnableView,
    ExtensionV1InstallView,
    ExtensionV1ListView,
    ExtensionV1RegistryView,
    ExtensionV1RollbackView,
    ExtensionV1UninstallView,
    ExtensionV1UpdateView,
    ExtensionV1UploadView,
)

app_name = namespace


class ExtensionApiV1ReverseViews:
    """
    Reverse view names for the Extensions REST api.

    Example
    -------
    .. code-block:: python

        from django.urls import reverse
        url = reverse(
            f"{ExtensionApiV1ReverseViews.namespace}:{ExtensionApiV1ReverseViews.enable}",
            kwargs={"slug": "weather"},
        )
    """

    namespace = f"api:v1:{namespace}"

    list_view = to_snake_case(ExtensionV1ListView.__name__)
    registry = to_snake_case(ExtensionV1RegistryView.__name__)
    check_updates = to_snake_case(ExtensionV1CheckUpdatesView.__name__)
    install = to_snake_case(ExtensionV1InstallView.__name__)
    upload = to_snake_case(ExtensionV1UploadView.__name__)
    detail = to_snake_case(ExtensionV1DetailView.__name__)
    enable = to_snake_case(ExtensionV1EnableView.__name__)
    disable = to_snake_case(ExtensionV1DisableView.__name__)
    update = to_snake_case(ExtensionV1UpdateView.__name__)
    rollback = to_snake_case(ExtensionV1RollbackView.__name__)
    configure = to_snake_case(ExtensionV1ConfigureView.__name__)
    availability = to_snake_case(ExtensionV1AvailabilityView.__name__)
    uninstall = to_snake_case(ExtensionV1UninstallView.__name__)


urlpatterns = [
    path("", ExtensionV1ListView.as_view(), name=ExtensionApiV1ReverseViews.list_view),
    path("registry/", ExtensionV1RegistryView.as_view(), name=ExtensionApiV1ReverseViews.registry),
    path("check-updates/", ExtensionV1CheckUpdatesView.as_view(), name=ExtensionApiV1ReverseViews.check_updates),
    path("install/", ExtensionV1InstallView.as_view(), name=ExtensionApiV1ReverseViews.install),
    path("upload/", ExtensionV1UploadView.as_view(), name=ExtensionApiV1ReverseViews.upload),
    path("<slug:slug>/", ExtensionV1DetailView.as_view(), name=ExtensionApiV1ReverseViews.detail),
    path("<slug:slug>/enable/", ExtensionV1EnableView.as_view(), name=ExtensionApiV1ReverseViews.enable),
    path("<slug:slug>/disable/", ExtensionV1DisableView.as_view(), name=ExtensionApiV1ReverseViews.disable),
    path("<slug:slug>/update/", ExtensionV1UpdateView.as_view(), name=ExtensionApiV1ReverseViews.update),
    path("<slug:slug>/rollback/", ExtensionV1RollbackView.as_view(), name=ExtensionApiV1ReverseViews.rollback),
    path("<slug:slug>/configure/", ExtensionV1ConfigureView.as_view(), name=ExtensionApiV1ReverseViews.configure),
    path(
        "<slug:slug>/availability/",
        ExtensionV1AvailabilityView.as_view(),
        name=ExtensionApiV1ReverseViews.availability,
    ),
    path("<slug:slug>/uninstall/", ExtensionV1UninstallView.as_view(), name=ExtensionApiV1ReverseViews.uninstall),
]
