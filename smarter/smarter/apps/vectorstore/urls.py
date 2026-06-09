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
from smarter.common.utils import to_snake_case

from .const import namespace

logger = logging.getLogger(__name__)

app_name = namespace


class VectorstoreReverseNames:
    """
    Holds named URL patterns for the vectorstore app.
    This class provides constants for all named URL patterns used in the vectorstore views.
    The names follow the convention: 'vectorstore_<view_name>'.
    These are referenced in Django templates as 'reverse' or 'url' tags.

    .. usage-example::

      .. html::

      <a href="{% url 'vectorstore:list_view' %}">Go to Vectorstore List View</a>

    """

    namespace = namespace

    list_view = to_snake_case(VectorstoreListView)
    manifest_view = to_snake_case(VectorstoreManifestView)


urlpatterns = []
if smarter_settings.enable_vectorstore:
    urlpatterns = [
        path("", VectorstoreListView.as_view(), name=VectorstoreReverseNames.list_view),
        path(
            "vectorstores/<str:backend>/<str:name>/manifest/",
            VectorstoreManifestView.as_view(),
            name=VectorstoreReverseNames.manifest_view,
        ),
    ]
    logger.info("%s Vectorstore API endpoints enabled.", formatted_text(__name__))
else:
    logger.info(
        "%s Vectorstore API endpoints have been disabled. Set env `SMARTER_ENABLE_VECTORSTORE=true` to enable.",
        formatted_text(__name__),
    )
