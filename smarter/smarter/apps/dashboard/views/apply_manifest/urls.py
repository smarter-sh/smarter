"""
URL configuration for the apply manifest views in the dashboard app.
"""

from django.urls import path

from smarter.common.conf import smarter_settings
from smarter.lib import logging

from .const import namespace
from .manifest_drop_zone import ManifestDropZoneView

app_name = namespace
logger = logging.getLogger(__name__)


class ApplyManifestReverseNames:
    """
    A class to hold the names of the apply manifest views for easy reference throughout the codebase.
    """

    namespace = namespace

    manifest_drop_zone = "manifest_drop_zone"


urlpatterns = []

if smarter_settings.enable_dashboard_apply:
    urlpatterns = [
        path("manifest-drop-zone/", ManifestDropZoneView.as_view(), name=ApplyManifestReverseNames.manifest_drop_zone),
    ]
    logger.info(
        "%s manifest drop zone enabled. Set env ENABLE_DASHBOARD_APPLY=false to disable.",
        logging.formatted_text(__name__),
    )
else:
    logger.info(
        "%s manifest drop zone disabled. Set env ENABLE_DASHBOARD_APPLY=true to enable.",
        logging.formatted_text(__name__),
    )
