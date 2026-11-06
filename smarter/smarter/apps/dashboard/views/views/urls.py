"""URL configuration for the web platform."""

from django.urls import path
from django.views.generic.base import RedirectView

from smarter.apps.dashboard.const import namespace
from smarter.apps.dashboard.views.views import DashboardView
from smarter.common.conf import smarter_settings
from smarter.common.mixins.helper_mixin import SmarterReadyState
from smarter.lib import logging

logger = logging.getLogger(__name__)


class DashboardReverseNames:
    """A class to hold the names of the dashboard views for easy reference throughout the codebase."""

    namespace = namespace

    dashboard = namespace


urlpatterns = [
    path("", DashboardView.as_view(), name=DashboardReverseNames.dashboard),
    path("help/", RedirectView.as_view(url="/docs/"), name="help"),
    path("support/", RedirectView.as_view(url="/docs/"), name="support"),
]

if smarter_settings.enable_dropzone_manifest_apply:
    logger.debug(
        "%s %s app dropzone url endpoint is %s. Set env 'ENABLE_MANIFEST_DROPZONE' to 'false' to disable.",
        logging.SmarterFormattedText.text(__name__),
        namespace,
        SmarterReadyState.READY,
    )
else:
    logger.info(
        "%s %s app dropzone url endpoint is %s. Set env 'ENABLE_MANIFEST_DROPZONE' to 'true' to enable.",
        logging.SmarterFormattedText.text(__name__),
        namespace,
        SmarterReadyState.NOT_READY,
    )
