"""
Django URL patterns for the prompt app. These are the
endpoints for for the Workbench React app and chat configuration.

how we got here:
 - /
 - /workbench/<str:name>/config/
"""

import logging

from django.urls import path

from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.utils import camel_case_object_name
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .const import namespace
from .views.terminal import TerminalEmulatorView
from .views.views import (
    ChatAppWorkbenchView,
    ChatConfigView,
    PromptLandingView,
    PromptListView,
    PromptManifestView,
)

logger = logging.getLogger(__name__)

app_name = namespace


class PromptReverseViews:
    """
    Reverse views for the Prompt app.
    Provides named references for reversing Prompt-related API endpoints.

    This class is used for reverse URL resolution in Django, where each attribute
    corresponds to a Prompt command endpoint. The names are derived from the actual
    API view class names, ensuring consistency and reducing the risk of typos
    when using Django's URL reversing features.

    All Prompt endpoints in the Smarter platform are included as attributes
    of this class. This centralizes the reverse URL names for all Prompt endpoints,
    making it easier to maintain and reference them throughout the codebase.

    Usage
    -----
    Use these attributes with Django's ``reverse()`` function or in templates
    to generate URLs for Prompt API endpoints based on the view class names.

    Example
    -------
    .. code-block:: python

        from django.urls import reverse
        url = reverse(PromptReverseViews.describe, kwargs={'hashed_id': 'rMTAwMDAzOQx'})

        # returns manifest of the chatbot with the given hashed_id
        retval = PromptReverseViews.describe
        print(retval)

    """

    namespace = namespace

    manifest_by_hashed_id = camel_case_object_name(PromptManifestView)
    chat_by_hashed_id = camel_case_object_name(ChatAppWorkbenchView)
    config_by_hashed_id = camel_case_object_name(ChatConfigView)
    landing_by_hashed_id = camel_case_object_name(PromptLandingView)
    terminal_emulator = camel_case_object_name(TerminalEmulatorView)


urlpatterns = [
    path("", PromptListView.as_view(), name="listview"),
    path("chatbots/<str:hashed_id>/", PromptLandingView.as_view(), name=PromptReverseViews.landing_by_hashed_id),
    path(
        "chatbots/<str:hashed_id>/manifest/",
        PromptManifestView.as_view(),
        name=PromptReverseViews.manifest_by_hashed_id,
    ),
    path(
        "chatbots/<str:hashed_id>/chat/",
        ChatAppWorkbenchView.as_view(),
        name=PromptReverseViews.chat_by_hashed_id,
    ),
    path("chatbots/<str:hashed_id>/config/", ChatConfigView.as_view(), name=PromptReverseViews.config_by_hashed_id),
]

if smarter_settings.enabled_terminal_app:
    urlpatterns.append(
        path("terminal-app/", TerminalEmulatorView.as_view(), name=PromptReverseViews.terminal_emulator),
    )
    logger_prefix = formatted_text(__name__)
    logger.info("%s Terminal app url endpoint enabled.", logger_prefix)
else:
    logger.info(
        "%s Terminal app is disabled. Set env `SMARTER_ENABLE_TERMINAL_APP=true` to enable the terminal emulator endpoint at /terminal-app/.",
        formatted_text(__name__),
    )
