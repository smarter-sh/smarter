"""
URL configuration for the vectorstore app.
"""

import logging

from django.urls import path

from smarter.apps.vectorstore.views import (
    VectorstoreListView,
    VectorstoreManifestView,
)
from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import formatted_text

from .const import namespace

logger = logging.getLogger(__name__)

app_name = namespace


urlpatterns = [
    path("", VectorstoreListView.as_view(), name="list_view"),
    path(
        "vectorstores/<str:backend>/<str:name>/manifest/",
        VectorstoreManifestView.as_view(),
        name="manifest_view",
    ),
]

if smarter_settings.enable_vectorstore:
    urlpatterns = [
        path("", VectorstoreListView.as_view(), name="list_view"),
        path(
            "vectorstores/<str:backend>/<str:name>/manifest/",
            VectorstoreManifestView.as_view(),
            name="manifest_view",
        ),
    ]
    logger.info("%s Vectorstore API endpoints enabled.", formatted_text(__name__))
else:
    urlpatterns = []
    logger.info(
        "%s Vectorstore API endpoints have been disabled. Set env `SMARTER_ENABLE_VECTORSTORE=true` to enable.",
        formatted_text(__name__),
    )
