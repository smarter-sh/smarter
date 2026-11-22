"""
URL configuration for the Dashboard app's dropzone views.

This module registers URL patterns for the prompt dropzone sub-application
of the dashboard. The page applies manifests with the public api's ``/api/v1/cli/apply/``. Registration is conditional on the
``SMARTER_APP_DASHBOARD_MANIFEST_DROPZONE_ENABLE`` setting: when disabled, no routes are
registered and an informational log message is emitted.

Attributes:
    app_name (str): The Django application namespace, taken from
        :data:`.const.namespace`.
    urlpatterns (list): The list of URL patterns registered for this app.
        Empty when ``smarter_settings.app_dashboard_manifest_dropzone_enable`` is
        ``False``.

Classes:
    PassthroughReverseNames: Convenience class that centralises the
        ``reverse()`` name strings used by this URL configuration.

Example:
    Include these URLs from a parent URL configuration::

        from django.urls import path

        urlpatterns = [
            path("dropzone/", include("smarter.apps.dashboard.views.dropzone.urls")),
        ]
"""

from django.urls import path

from smarter.common.conf import smarter_settings
from smarter.common.mixins.helper_mixin import SmarterReadyState
from smarter.lib import logging

from .const import namespace
from .names import DropzoneReverseNames
from .view import DropzoneView

app_name = namespace
logger = logging.getSmarterLogger(__name__)


urlpatterns = []

if smarter_settings.app_dashboard_manifest_dropzone_enable:
    urlpatterns = [
        path("", DropzoneView.as_view(), name=DropzoneReverseNames.dropzone),
    ]
    logger.debug(
        "%s app dropzone url endpoint is %s. Set env 'SMARTER_APP_DASHBOARD_MANIFEST_DROPZONE_ENABLE' to 'false' to disable.",
        app_name,
        SmarterReadyState.READY,
    )
else:
    logger.info(
        "%s app dropzone url endpoint is %s. Set env 'SMARTER_APP_DASHBOARD_MANIFEST_DROPZONE_ENABLE' to 'true' to enable.",
        app_name,
        SmarterReadyState.NOT_READY,
    )
