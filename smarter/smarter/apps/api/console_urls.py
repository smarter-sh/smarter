"""URL configuration for smarter project."""

import logging

from django.urls import path

from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.utils import camel_case_object_name

from .const import namespace
from .views import ManifestDropZoneView

logger = logging.getLogger(__name__)

app_name = namespace

if smarter_settings.enable_file_drop_zone:
    urlpatterns = [
        path(
            "",
            ManifestDropZoneView.as_view(),
            name=camel_case_object_name(ManifestDropZoneView),
        ),
    ]
    logger.info("%s File Drop Zone API endpoint enabled.", formatted_text(__name__))
else:
    urlpatterns = []
    logger.info(
        "%s File Drop Zone API endpoint has been disabled. Set env `SMARTER_ENABLE_FILE_DROP_ZONE=true` to enable.",
        formatted_text(__name__),
    )
