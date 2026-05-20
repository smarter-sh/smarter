# pylint: disable=W0613,C0302
"""
PromptListView is a Django class-based view that serves the list of ChatBots
for the Smarter workbench web console. It is responsible for fetching the
ChatBots associated with the authenticated user, as well as any shared ChatBots,
and rendering them in a template. The view is protected and requires the user
to be authenticated. It also includes caching to keep the workbench snappy while
avoiding appearing stale.
"""

from http import HTTPStatus
from typing import Optional

from django.db import models
from django.http import (
    HttpRequest,
)
from django.http.response import JsonResponse

from smarter.apps.account.serializers import UserProfileSerializer
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.chatbot.models import (
    ChatBot,
    ChatBotHelper,
)
from smarter.apps.chatbot.serializers import ChatBotSerializer
from smarter.apps.chatbot.utils import get_cached_chatbots_for_user_profile
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import (
    SmarterAuthenticatedWebView,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

WORKBENCH_CACHE_TIMEOUT = 30  # 30 seconds. keeps the workbench snappy while avoiding appearing stale.


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING])


def should_log_verbose(level):
    """Check if logging should be done based on the waffle switch."""
    return smarter_settings.verbose_logging


verbose_logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING], condition_func=should_log_verbose
)


class PromptListApiView(SmarterAuthenticatedWebView):
    """
    list view for smarter workbench web console. This view is protected and
    requires the user to be authenticated. It generates cards for each
    ChatBots.
    """

    chatbots: Optional[models.QuerySet[ChatBot]] = None
    chatbot_helpers: list[ChatBotHelper] = []

    def post(self, request: HttpRequest, *args, **kwargs):

        @cache_results(timeout=WORKBENCH_CACHE_TIMEOUT)
        def _get_cached_chatbots_for_user_profile(user_profile_id: int) -> JsonResponse:
            """Get cached chatbots for a user profile."""

            # pylint: disable=C0415
            from smarter.apps.prompt.urls import PromptReverseNames

            self.chatbot_helpers = get_cached_chatbots_for_user_profile(user_profile_id=self.user_profile.id)  # type: ignore

            user_chatbots = [
                {
                    **ChatBotSerializer(chatbot_helper.chatbot).data,
                    "urls": {
                        "manifest": reverse(":".join([PromptReverseNames.namespace, PromptReverseNames.manifest_by_hashed_id]), kwargs={"hashed_id": chatbot_helper.chatbot.hashed_id}),  # type: ignore
                        "chat": reverse(":".join([PromptReverseNames.namespace, PromptReverseNames.chat_by_hashed_id]), kwargs={"hashed_id": chatbot_helper.chatbot.hashed_id}),  # type: ignore
                        "config": reverse(":".join([PromptReverseNames.namespace, PromptReverseNames.config_by_hashed_id]), kwargs={"hashed_id": chatbot_helper.chatbot.hashed_id}),  # type: ignore
                    },
                }
                for chatbot_helper in self.chatbot_helpers
                if chatbot_helper.chatbot.user_profile == self.user_profile  # type: ignore
            ]
            shared_chatbots = [
                {
                    **ChatBotSerializer(chatbot_helper.chatbot).data,
                    "urls": {
                        "manifest": reverse(":".join([PromptReverseNames.namespace, PromptReverseNames.manifest_by_hashed_id]), kwargs={"hashed_id": chatbot_helper.chatbot.hashed_id}),  # type: ignore
                        "chat": reverse(":".join([PromptReverseNames.namespace, PromptReverseNames.chat_by_hashed_id]), kwargs={"hashed_id": chatbot_helper.chatbot.hashed_id}),  # type: ignore
                        "config": reverse(":".join([PromptReverseNames.namespace, PromptReverseNames.config_by_hashed_id]), kwargs={"hashed_id": chatbot_helper.chatbot.hashed_id}),  # type: ignore
                    },
                }
                for chatbot_helper in self.chatbot_helpers
                if chatbot_helper.chatbot.user_profile != self.user_profile  # type: ignore
            ]

            smarter_admin = smarter_cached_objects.smarter_admin_user_profile
            retval = {
                "user": UserProfileSerializer(self.user_profile).data,
                "admin": UserProfileSerializer(smarter_admin).data,
                "chatbots": {
                    "user": user_chatbots,
                    "shared": shared_chatbots,
                },
            }
            logger.debug(
                "%s.post() caching prompt list for user %s with retval: %s",
                self.formatted_class_name,
                self.user_profile,
                logging.formatted_json(retval),
            )
            return JsonResponse(retval)

        return _get_cached_chatbots_for_user_profile(user_profile_id=self.user_profile.id)  # type: ignore


class PromptListApiCloneView(SmarterAuthenticatedWebView):
    """
    API view for cloning a ChatBot. This view is protected and requires the user to be authenticated.
    """

    def post(self, request: HttpRequest, *args, **kwargs):
        chatbot_id = kwargs.get("chatbot_id")
        new_name = kwargs.get("new_name")
        chatbot: ChatBot

        if not chatbot_id or not new_name:
            return JsonResponse({"error": "chatbot_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            chatbot = ChatBot.objects.get(id=chatbot_id)
        except ChatBot.DoesNotExist:
            return JsonResponse({"error": f"ChatBot with id {chatbot_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            cloned_chatbot = chatbot.clone(new_name=new_name, user_profile=self.user_profile)  # type: ignore
            data = ChatBotSerializer(cloned_chatbot).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("Error cloning ChatBot with id %s: %s", chatbot_id, str(e), exc_info=True)
            return JsonResponse(
                {"error": f"An error occurred while cloning the ChatBot: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class PromptListApiDeleteView(SmarterAuthenticatedWebView):
    """
    API view for deleting a ChatBot. This view is protected and requires the user to be authenticated.
    """

    def post(self, request: HttpRequest, *args, **kwargs):
        chatbot_id = kwargs.get("chatbot_id")
        if not chatbot_id:
            return JsonResponse({"error": "chatbot_id is required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            chatbot = ChatBot.objects.with_ownership_permission_for(self.user_profile.user).get(id=chatbot_id)  # type: ignore
        except ChatBot.DoesNotExist:
            return JsonResponse({"error": f"ChatBot with id {chatbot_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            chatbot.delete()
            return JsonResponse(
                {"message": f"ChatBot with id {chatbot_id} deleted successfully."}, status=HTTPStatus.OK
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("Error deleting ChatBot with id %s: %s", chatbot_id, str(e), exc_info=True)
            return JsonResponse(
                {"error": f"An error occurred while deleting the ChatBot: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class PromptListApiRenameView(SmarterAuthenticatedWebView):
    """
    API view for renaming a ChatBot. This view is protected and requires the user to be authenticated.
    """

    def post(self, request: HttpRequest, *args, **kwargs):
        chatbot_id = kwargs.get("chatbot_id")
        new_name = kwargs.get("new_name")
        if not chatbot_id or not new_name:
            return JsonResponse({"error": "chatbot_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            chatbot = ChatBot.objects.with_ownership_permission_for(self.user_profile.user).get(id=chatbot_id)  # type: ignore
        except ChatBot.DoesNotExist:
            return JsonResponse({"error": f"ChatBot with id {chatbot_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            chatbot.rename(new_name=new_name)
            data = ChatBotSerializer(chatbot).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("Error renaming ChatBot with id %s: %s", chatbot_id, str(e), exc_info=True)
            return JsonResponse(
                {"error": f"An error occurred while renaming the ChatBot: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )
