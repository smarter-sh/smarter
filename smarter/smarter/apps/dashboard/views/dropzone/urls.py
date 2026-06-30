"""
URL configuration for the Dashboard app's dropzone views.

This module registers URL patterns for the prompt dropzone sub-application
of the dashboard. Registration is conditional on the
``ENABLE_DASHBOARD_PASSTHROUGH_PROMPT`` setting: when disabled, no routes are
registered and an informational log message is emitted.

Attributes:
    app_name (str): The Django application namespace, taken from
        :data:`.const.namespace`.
    urlpatterns (list): The list of URL patterns registered for this app.
        Empty when ``smarter_settings.enable_dashboard_dropzone_prompt`` is
        ``False``.

Classes:
    PassthroughReverseNames: Convenience class that centralises the
        ``reverse()`` name strings used by this URL configuration.

Example:
    Include these URLs from a parent URL configuration::

        from django.urls import include, path

        urlpatterns = [
            path("dropzone/", include("smarter.apps.dashboard.views.dropzone.urls")),
        ]
"""

from django.urls import include, path

from smarter.common.conf import smarter_settings
from smarter.common.mixins.helper_mixin import SmarterReadyState
from smarter.lib import logging

from .api import urls as api_urls
from .const import namespace
from .names import DropzoneReverseNames
from .view import DropzoneView

app_name = namespace
logger = logging.getLogger(__name__)


urlpatterns = []

if smarter_settings.enable_dropzone_manifest_apply:
    urlpatterns = [
        path("", DropzoneView.as_view(), name=DropzoneReverseNames.dropzone),
        path("api/", include(api_urls, api_urls.namespace)),
    ]
    logger.info(
        "%s %s app dropzone url endpoint is %s. Set env 'ENABLE_MANIFEST_DROPZONE' to 'false' to disable.",
        logging.formatted_text(__name__),
        app_name,
        SmarterReadyState.READY,
    )
else:
    logger.info(
        "%s %s app dropzone url endpoint is %s. Set env 'ENABLE_MANIFEST_DROPZONE' to 'true' to enable.",
        logging.formatted_text(__name__),
        app_name,
        SmarterReadyState.NOT_READY,
    )
