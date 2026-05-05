# pylint: disable=W0613,C0302
"""
PromptListView is a Django class-based view that serves the list of ChatBots
for the Smarter workbench web console. It is responsible for fetching the
ChatBots associated with the authenticated user, as well as any shared ChatBots,
and rendering them in a template. The view is protected and requires the user
to be authenticated. It also includes caching to keep the workbench snappy while
avoiding appearing stale.
"""

from typing import Optional

from django.db import models
from django.http import (
    HttpRequest,
)
from django.http.response import JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control

from smarter.apps.account.serializers import UserProfileSerializer
from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.apps.chatbot.models import (
    ChatBot,
    ChatBotHelper,
)
from smarter.apps.chatbot.serializers import ChatBotSerializer
from smarter.apps.chatbot.utils import get_cached_chatbots_for_user_profile
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.views import (
    SmarterAuthenticatedWebView,
    smarter_cache_page_by_user,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

WORKBENCH_CACHE_TIMEOUT = 10  # 10 seconds. keeps the workbench snappy while avoiding appearing stale.


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING])


def should_log_verbose(level):
    """Check if logging should be done based on the waffle switch."""
    return smarter_settings.verbose_logging


verbose_logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING], condition_func=should_log_verbose
)


@method_decorator(cache_control(max_age=WORKBENCH_CACHE_TIMEOUT), name="post")
@method_decorator(smarter_cache_page_by_user(WORKBENCH_CACHE_TIMEOUT), name="post")
class PromptListApiView(SmarterAuthenticatedWebView):
    """
    list view for smarter workbench web console. This view is protected and
    requires the user to be authenticated. It generates cards for each
    ChatBots.
    """

    chatbots: Optional[models.QuerySet[ChatBot]] = None
    chatbot_helpers: list[ChatBotHelper] = []

    def post(self, request: HttpRequest, *args, **kwargs):

        # pylint: disable=C0415
        from smarter.apps.prompt.urls import PromptReverseViews

        logger.debug(
            "%s.post() called for %s with args %s, kwargs %s", self.formatted_class_name, request, args, kwargs
        )

        self.chatbot_helpers = get_cached_chatbots_for_user_profile(user_profile_id=self.user_profile.id)  # type: ignore

        user_chatbots = [
            {
                **ChatBotSerializer(chatbot_helper.chatbot).data,
                "urls": {
                    "manifest": reverse(":".join([PromptReverseViews.namespace, PromptReverseViews.manifest_by_hashed_id]), kwargs={"hashed_id": chatbot_helper.chatbot.hashed_id}),  # type: ignore
                    "chat": reverse(":".join([PromptReverseViews.namespace, PromptReverseViews.chat_by_hashed_id]), kwargs={"hashed_id": chatbot_helper.chatbot.hashed_id}),  # type: ignore
                    "config": reverse(":".join([PromptReverseViews.namespace, PromptReverseViews.config_by_hashed_id]), kwargs={"hashed_id": chatbot_helper.chatbot.hashed_id}),  # type: ignore
                },
            }
            for chatbot_helper in self.chatbot_helpers
            if chatbot_helper.chatbot.user_profile == self.user_profile  # type: ignore
        ]
        shared_chatbots = [
            {
                **ChatBotSerializer(chatbot_helper.chatbot).data,
                "urls": {
                    "manifest": reverse(":".join([PromptReverseViews.namespace, PromptReverseViews.manifest_by_hashed_id]), kwargs={"hashed_id": chatbot_helper.chatbot.hashed_id}),  # type: ignore
                    "chat": reverse(":".join([PromptReverseViews.namespace, PromptReverseViews.chat_by_hashed_id]), kwargs={"hashed_id": chatbot_helper.chatbot.hashed_id}),  # type: ignore
                    "config": reverse(":".join([PromptReverseViews.namespace, PromptReverseViews.config_by_hashed_id]), kwargs={"hashed_id": chatbot_helper.chatbot.hashed_id}),  # type: ignore
                },
            }
            for chatbot_helper in self.chatbot_helpers
            if chatbot_helper.chatbot.user_profile != self.user_profile  # type: ignore
        ]

        smarter_admin = get_cached_smarter_admin_user_profile()
        retval = {
            "user": UserProfileSerializer(self.user_profile).data,
            "admin": UserProfileSerializer(smarter_admin).data,
            "chatbots": {
                "user": user_chatbots,
                "shared": shared_chatbots,
            },
        }
        verbose_logger.debug(
            "%s.post() rendering template %s with retval: %s",
            self.formatted_class_name,
            self.template_path,
            logging.formatted_json(retval),
        )
        return JsonResponse(retval)
