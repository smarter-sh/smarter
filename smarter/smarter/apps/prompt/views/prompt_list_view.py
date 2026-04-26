# pylint: disable=W0613,C0302
"""
Views for the React chat component used in the Smarter web application.
"""

import logging
from typing import Optional

from django.db import models
from django.http import (
    HttpRequest,
)
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.apps.chatbot.models import (
    ChatBot,
    ChatBotHelper,
)
from smarter.apps.chatbot.utils import get_cached_chatbots_for_user_profile
from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import formatted_json
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseForbidden,
)
from smarter.lib.django.views import (
    SmarterAuthenticatedWebView,
    smarter_cache_page_by_user,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

WORKBENCH_CACHE_TIMEOUT = 10  # 10 seconds. keeps the workbench snappy while avoiding appearing stale.


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


def should_log_verbose(level):
    """Check if logging should be done based on the waffle switch."""
    return smarter_settings.verbose_logging


verbose_logger = WaffleSwitchedLoggerWrapper(base_logger, should_log_verbose)


@method_decorator(cache_control(max_age=WORKBENCH_CACHE_TIMEOUT), name="dispatch")
@method_decorator(smarter_cache_page_by_user(WORKBENCH_CACHE_TIMEOUT), name="dispatch")
class PromptListView(SmarterAuthenticatedWebView):
    """
    list view for smarter workbench web console. This view is protected and
    requires the user to be authenticated. It generates cards for each
    ChatBots.
    """

    template_path = "prompt/listview.html"
    chatbots: Optional[models.QuerySet[ChatBot]] = None
    chatbot_helpers: list[ChatBotHelper] = []

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        # pylint: disable=C0415
        if not isinstance(self.user_profile, UserProfile):
            logger.error(
                "%s.dispatch() - user_profile is not set or not an instance of UserProfile. This should not happen. Returning 403.",
                self.formatted_class_name,
            )
            return SmarterHttpResponseForbidden(request=request, error_message="Authentication required")

        from smarter.apps.prompt.urls import PromptReverseViews

        logger.debug(
            "%s.dispatch() called for %s with args %s, kwargs %s", self.formatted_class_name, request, args, kwargs
        )
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code >= 300:
            return response

        self.chatbot_helpers = get_cached_chatbots_for_user_profile(user_profile_id=self.user_profile.id)  # type: ignore

        user_chatbots = [
            chatbot_helper
            for chatbot_helper in self.chatbot_helpers
            if chatbot_helper.chatbot.user_profile == self.user_profile  # type: ignore
        ]
        shared_chatbots = [
            chatbot_helper
            for chatbot_helper in self.chatbot_helpers
            if chatbot_helper.chatbot.user_profile != self.user_profile  # type: ignore
        ]

        smarter_admin = get_cached_smarter_admin_user_profile()
        context = {
            "prompt_list": {
                "smarter_admin": smarter_admin,
                "user_chatbots": user_chatbots,
                "user_chatbots_count": len(user_chatbots),
                "shared_chatbots": shared_chatbots,
            },
            "reverse_views": {
                "manifest": f"{PromptReverseViews.namespace}:{PromptReverseViews.manifest_by_hashed_id}",
                "chat": f"{PromptReverseViews.namespace}:{PromptReverseViews.chat_by_hashed_id}",
                "config": f"{PromptReverseViews.namespace}:{PromptReverseViews.config_by_hashed_id}",
            },
        }
        verbose_logger.debug(
            "%s.dispatch() rendering template %s with context: %s",
            self.formatted_class_name,
            self.template_path,
            formatted_json(context),
        )
        return render(request, template_name=self.template_path, context=context)
