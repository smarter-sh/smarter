"""
URL configuration for the Dashboard app's passthrough views.

This module registers URL patterns for the prompt passthrough sub-application
of the dashboard. Registration is conditional on the
``ENABLE_DASHBOARD_PASSTHROUGH_PROMPT`` setting: when disabled, no routes are
registered and an informational log message is emitted.

Attributes:
    app_name (str): The Django application namespace, taken from
        :data:`.const.namespace`.
    urlpatterns (list): The list of URL patterns registered for this app.
        Empty when ``smarter_settings.enable_dashboard_passthrough_prompt`` is
        ``False``.

Classes:
    PassthroughReverseNames: Convenience class that centralises the
        ``reverse()`` name strings used by this URL configuration.

Example:
    Include these URLs from a parent URL configuration::

        from django.urls import include, path

        urlpatterns = [
            path("passthrough/", include("smarter.apps.dashboard.views.passthrough.urls")),
        ]
"""

from django.urls import include, path

from smarter.common.conf import smarter_settings
from smarter.common.mixins.helper_mixin import SmarterReadyState
from smarter.common.utils import to_snake_case
from smarter.lib import logging

from .api import urls as api_urls
from .const import namespace
from .view import PromptPassthroughView

app_name = namespace
logger = logging.getLogger(__name__)


class PassthroughReverseNames:
    """A class to hold the namespace for the passthrough views in the dashboard app."""

    namespace = namespace

    view = to_snake_case(PromptPassthroughView.__name__)


urlpatterns = []

if smarter_settings.enable_dashboard_passthrough_prompt:
    urlpatterns = [
        path("", PromptPassthroughView.as_view(), name=PassthroughReverseNames.view),
        path("api/", include(api_urls, api_urls.namespace)),
    ]
    logger.info(
        "%s %s app passthrough url endpoint is %s. Set env 'ENABLE_DASHBOARD_PASSTHROUGH_PROMPT' to 'false' to disable.",
        logging.formatted_text(__name__),
        app_name,
        SmarterReadyState.READY,
    )
else:
    logger.info(
        "%s %s app passthrough url endpoint is %s. Set env 'ENABLE_DASHBOARD_PASSTHROUGH_PROMPT' to 'true' to enable.",
        logging.formatted_text(__name__),
        app_name,
        SmarterReadyState.NOT_READY,
    )
