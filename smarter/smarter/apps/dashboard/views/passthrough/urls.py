"""URL configuration for the Dashboard app's passthrough views."""

from django.urls import include, path

from smarter.common.conf import smarter_settings
from smarter.common.utils import camel_case_object_name
from smarter.lib import logging

from .api import urls as api_urls
from .const import namespace
from .view import PromptPassthroughView

app_name = namespace
logger = logging.getLogger(__name__)


class PassthroughReverseNames:
    """
    A class to hold the namespace for the passthrough views in the dashboard app.
    """

    namespace = namespace

    view = camel_case_object_name(PromptPassthroughView)


urlpatterns = []

if smarter_settings.enable_dashboard_passthrough_prompt:
    urlpatterns = [
        path("", PromptPassthroughView.as_view(), name=PassthroughReverseNames.view),
        path("api/", include(api_urls, api_urls.namespace)),
    ]
    logger.info(
        "%s passthrough prompt views enabled. Set env 'ENABLE_DASHBOARD_PASSTHROUGH_PROMPT' to 'true' to enable.",
        logging.formatted_text(__file__),
    )
else:
    logger.info(
        "%s passthrough prompt views disabled. Set env 'ENABLE_DASHBOARD_PASSTHROUGH_PROMPT' to 'false' to disable.",
        logging.formatted_text(__file__),
    )
