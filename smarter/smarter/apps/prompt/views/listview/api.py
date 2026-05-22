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

from django.core.paginator import Paginator
from django.db import models
from django.http import (
    HttpRequest,
)
from django.http.response import JsonResponse

from smarter.apps.account.serializers import UserProfileSerializer
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.chatbot.models import ChatBot
from smarter.apps.chatbot.serializers import ChatBotSerializer
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.views import (
    SmarterAuthenticatedWebView,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

WORKBENCH_CACHE_TIMEOUT = 30  # 30 seconds. keeps the workbench snappy while avoiding appearing stale.
DEFAULT_PAGE_SIZE = 25  # default number of chatbots to return per page in the API response


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING])


def should_log_verbose(level):
    """Check if logging should be done based on the waffle switch."""
    return smarter_settings.verbose_logging


verbose_logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING], condition_func=should_log_verbose
)


class PromptListOwnershipFilter:
    """
    Enum-like class for ownership filter options in the PromptListApiView.
    """

    OWNED = "owned"
    SHARED = "shared"
    ALL = "all"


class PromptListApiView(SmarterAuthenticatedWebView):
    """
    List API view for the Smarter workbench web console.

    This view returns a paginated list of ChatBots accessible to the authenticated
    user, supporting filters for owned, shared, or all ChatBots. Results are
    cached for responsiveness, with optional cache invalidation. User
    authentication is required.

    Example URL Paths:
        /workbench/api/listview/
        /workbench/api/listview/all/
        /workbench/api/listview/all/?page=1&page_size=50&invalidate_cache=false
        /workbench/api/listview/owned/
        /workbench/api/listview/owned/?page=1&page_size=25&invalidate_cache=true
        /workbench/api/listview/shared/
        /workbench/api/listview/shared/?page=2&page_size=10&invalidate_cache=false

    Features:
        - Returns paginated ChatBots for the authenticated user.
        - Supports filtering by 'owned', 'shared', or 'all'.
        - Caches results for improved performance.
        - Allows cache invalidation via request.
        - Requires user authentication.

    Attributes:
        WORKBENCH_CACHE_TIMEOUT (int): Cache timeout in seconds.
        DEFAULT_PAGE_SIZE (int): Default number of ChatBots per page.

    Methods:
        post(request, *args, **kwargs):
            Handles POST requests to retrieve ChatBots based on filters and
            pagination.

            Keyword Args:
                ownership_filter (str, optional): 'owned', 'shared', or 'all'.
                    Defaults to 'all'.
                page (int, optional): Page number for pagination. Defaults to 1.
                invalidate_cache (bool, optional): If true, invalidates cache
                    before fetching results. Defaults to False.
                page_size (int, optional): Number of ChatBots per page. Defaults
                    to DEFAULT_PAGE_SIZE.
    """

    def post(self, request: HttpRequest, *args, **kwargs):

        qs: models.QuerySet[ChatBot]
        user_profile_id = self.user_profile.id  # type: ignore
        ownership_filter = kwargs.get("ownership_filter", PromptListOwnershipFilter.ALL)
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", DEFAULT_PAGE_SIZE)
        invalidate_cache = request.GET.get("invalidate_cache", "false").lower() == "true"

        logger.debug(
            "%s.post() Received request with ownership_filter=%s, page=%s, page_size=%s, invalidate_cache=%s",
            self.formatted_class_name,
            ownership_filter,
            page,
            page_size,
            invalidate_cache,
        )

        if ownership_filter not in [
            PromptListOwnershipFilter.OWNED,
            PromptListOwnershipFilter.SHARED,
            PromptListOwnershipFilter.ALL,
        ]:
            logger.warning(
                "%s.post() Received an invalid ownership_filter value: %s. Must be one of 'owned', 'shared', or 'all'. Defaulting to 'all'.",
                self.formatted_class_name,
                ownership_filter,
            )
            return JsonResponse(
                {"error": "Invalid ownership_filter. Must be one of 'owned', 'shared', or 'all'."},
                status=HTTPStatus.BAD_REQUEST,
            )

        @cache_results(timeout=WORKBENCH_CACHE_TIMEOUT)
        def _get_cached_chatbots_owned_by_user_profile(user_profile_id: int) -> models.QuerySet[ChatBot]:
            logger.debug(
                "%s.post() Fetching ChatBots owned by %s",
                self.formatted_class_name,
                self.user_profile,
            )
            retval = ChatBot.objects.owned_by(self.user_profile.user)  # type: ignore
            logger.debug(
                "%s.post() Fetching ChatBots owned by %s: %s",
                self.formatted_class_name,
                self.user_profile,
                logging.formatted_json(ChatBotSerializer(retval, many=True).data),
            )
            return retval

        @cache_results(timeout=WORKBENCH_CACHE_TIMEOUT)
        def _get_cached_chatbots_shared_with_user_profile(user_profile_id: int) -> models.QuerySet[ChatBot]:
            logger.debug(
                "%s.post() Fetching ChatBots shared with %s",
                self.formatted_class_name,
                self.user_profile,
            )
            retval = ChatBot.objects.shared_with(self.user_profile.user)  # type: ignore
            logger.debug(
                "%s.post() Fetching ChatBots shared with %s: %s",
                self.formatted_class_name,
                self.user_profile,
                logging.formatted_json(ChatBotSerializer(retval, many=True).data),
            )
            return retval

        @cache_results(timeout=WORKBENCH_CACHE_TIMEOUT)
        def _get_cached_chatbots_available_to_user_profile(user_profile_id) -> models.QuerySet[ChatBot]:
            logger.debug(
                "%s.post() Fetching ChatBots available to %s",
                self.formatted_class_name,
                self.user_profile,
            )
            retval = ChatBot.objects.with_read_permission_for(self.user_profile.user)  # type: ignore
            logger.debug(
                "%s.post() Fetching ChatBots available to %s: %s",
                self.formatted_class_name,
                self.user_profile,
                logging.formatted_json(ChatBotSerializer(retval, many=True).data),
            )
            return retval

        if invalidate_cache:
            logger.debug(
                "%s.post() Invalidating cache for ChatBots owned by %s",
                self.formatted_class_name,
                self.user_profile,
            )
            _get_cached_chatbots_owned_by_user_profile.invalidate(user_profile_id=user_profile_id)
            _get_cached_chatbots_available_to_user_profile.invalidate(user_profile_id=user_profile_id)

        if ownership_filter == PromptListOwnershipFilter.OWNED:
            qs = _get_cached_chatbots_owned_by_user_profile(user_profile_id=user_profile_id)

        elif ownership_filter == PromptListOwnershipFilter.SHARED:
            qs = _get_cached_chatbots_shared_with_user_profile(user_profile_id=user_profile_id)

        else:
            qs = _get_cached_chatbots_available_to_user_profile(user_profile_id=user_profile_id)

        paginator = Paginator(qs.order_by("-updated_at"), page_size)
        chatbots = paginator.get_page(page)

        smarter_admin = smarter_cached_objects.smarter_admin_user_profile
        retval = {
            "user": UserProfileSerializer(self.user_profile).data,
            "admin": UserProfileSerializer(smarter_admin).data,
            "chatbots": ChatBotSerializer(chatbots, many=True).data,
        }
        return JsonResponse(retval)


class PromptListApiCloneView(SmarterAuthenticatedWebView):
    """
    API view for cloning a ChatBot. This view is protected and requires the user to be authenticated.
    """

    def post(self, request: HttpRequest, *args, **kwargs):
        chatbot_id = kwargs.get("chatbot_id")
        new_name = kwargs.get("new_name")
        chatbot: ChatBot

        if not chatbot_id or not new_name:
            logging.warning(
                "%s.post() Missing required parameters. chatbot_id: %s, new_name: %s",
                self.formatted_class_name,
                chatbot_id,
                new_name,
            )
            return JsonResponse({"error": "chatbot_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            chatbot = ChatBot.objects.get(id=chatbot_id)
        except ChatBot.DoesNotExist:
            logger.warning("%s.post() ChatBot with id %s not found for cloning.", self.formatted_class_name, chatbot_id)
            return JsonResponse({"error": f"ChatBot with id {chatbot_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            cloned_chatbot = chatbot.clone(new_name=new_name, user_profile=self.user_profile)  # type: ignore
            data = ChatBotSerializer(cloned_chatbot).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error cloning ChatBot with id %s: %s",
                self.formatted_class_name,
                chatbot_id,
                str(e),
                exc_info=True,
            )
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
            logger.warning("%s.post() Missing required parameter chatbot_id for deletion.", self.formatted_class_name)
            return JsonResponse({"error": "chatbot_id is required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            chatbot = ChatBot.objects.with_ownership_permission_for(self.user_profile.user).get(id=chatbot_id)  # type: ignore
        except ChatBot.DoesNotExist:
            logger.warning(
                "%s.post() ChatBot with id %s not found for deletion.", self.formatted_class_name, chatbot_id
            )
            return JsonResponse({"error": f"ChatBot with id {chatbot_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            chatbot.delete()
            return JsonResponse(
                {"message": f"ChatBot with id {chatbot_id} deleted successfully."}, status=HTTPStatus.OK
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error deleting ChatBot with id %s: %s",
                self.formatted_class_name,
                chatbot_id,
                str(e),
                exc_info=True,
            )
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
            logger.warning(
                "%s.post() Missing required parameters for renaming. chatbot_id: %s, new_name: %s",
                self.formatted_class_name,
                chatbot_id,
                new_name,
            )
            return JsonResponse({"error": "chatbot_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            chatbot = ChatBot.objects.with_ownership_permission_for(self.user_profile.user).get(id=chatbot_id)  # type: ignore
        except ChatBot.DoesNotExist:
            logger.warning(
                "%s.post() ChatBot with id %s not found for renaming.", self.formatted_class_name, chatbot_id
            )
            return JsonResponse({"error": f"ChatBot with id {chatbot_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            chatbot.rename(new_name=new_name)
            data = ChatBotSerializer(chatbot).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error renaming ChatBot with id %s: %s",
                self.formatted_class_name,
                chatbot_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while renaming the ChatBot: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )
