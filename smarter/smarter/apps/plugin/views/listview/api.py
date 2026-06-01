# pylint: disable=W0613
"""
smarter.apps.plugin.views.plugin
This module contains views to implement the card-style list view
in the Smarter Dashboard.
"""

import logging
from http import HTTPStatus
from typing import Union

from django.core.handlers.asgi import ASGIRequest
from django.core.paginator import Paginator
from django.db import models
from django.http import HttpRequest, JsonResponse

from smarter.apps.account.serializers import UserProfileSerializer
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.plugin.caching import (
    get_cached_plugins_available_to_user_profile,
    get_cached_plugins_owned_by_user_profile,
    get_cached_plugins_shared_with_user_profile,
    invalidate_all_cached_plugins_for_user_profile,
)
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.serializers import PluginSerializer
from smarter.common.enum import SmarterResourceOwnershipFilterEnum
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
)
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)


DEFAULT_PAGE_SIZE = 25

base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class PluginListApiView(SmarterAuthenticatedNeverCachedWebView):
    """
    Render the plugin list view for the Smarter Workbench web console.

    This view displays all plugins available to the authenticated user as cards, providing a quick overview and access to plugin details.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    :returns: Rendered HTML page with a card for each plugin, or a 404 error page if the user is not authenticated.
    :rtype: HttpResponse
    """

    def post(self, request: ASGIRequest, *args, **kwargs) -> Union[JsonResponse, SmarterHttpResponseNotFound]:
        qs: models.QuerySet[PluginMeta]
        ownership_filter = kwargs.get("ownership_filter", SmarterResourceOwnershipFilterEnum.ALL)
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", DEFAULT_PAGE_SIZE)
        invalidate_cache = request.GET.get("invalidate_cache", "false").lower() == "true"

        logger.debug(
            "%s.get() Rendering plugin list view for user %s with args=%s, kwargs=%s.",
            self.formatted_class_name,
            request.user.username if request.user else "None",  # type: ignore[union-attr]
            args,
            kwargs,
        )
        if invalidate_cache:
            invalidate_all_cached_plugins_for_user_profile(user_profile=self.user_profile)  # type: ignore

        if ownership_filter == SmarterResourceOwnershipFilterEnum.OWNED:
            qs = get_cached_plugins_owned_by_user_profile(user_profile=self.user_profile)  # type: ignore

        elif ownership_filter == SmarterResourceOwnershipFilterEnum.SHARED:
            qs = get_cached_plugins_shared_with_user_profile(user_profile=self.user_profile)  # type: ignore

        elif ownership_filter == SmarterResourceOwnershipFilterEnum.ALL:
            qs = get_cached_plugins_available_to_user_profile(user_profile=self.user_profile)  # type: ignore
        else:
            logger.warning(
                "%s.post() Received an invalid ownership_filter value: %s. Must be one of 'owned', 'shared', or 'all'. Defaulting to 'all'.",
                self.formatted_class_name,
                ownership_filter,
            )
            return JsonResponse(
                {"error": "Invalid ownership_filter. Must be one of 'owned', 'shared', or 'all'."},
                status=HTTPStatus.BAD_REQUEST,
            )

        paginator = Paginator(qs.order_by("-updated_at"), page_size)
        plugins = paginator.get_page(page)

        smarter_admin = smarter_cached_objects.smarter_admin_user_profile
        retval = {
            "user": UserProfileSerializer(self.user_profile).data,
            "admin": UserProfileSerializer(smarter_admin).data,
            "objects": PluginSerializer(plugins, many=True).data,
        }
        return JsonResponse(retval)


class PluginListApiCloneView(SmarterAuthenticatedNeverCachedWebView):
    """
    Clone a plugin for the authenticated user.
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to clone an existing PluginMeta. Validates input
        parameters, checks for the existence of the PluginMeta to be cloned, and
        creates a new PluginMeta with the specified name. Invalidates the cache
        for the user's ChatBots after cloning.

        :param request: The HTTP request object containing the parameters for cloning.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - chatbot_id (str): The ID of the PluginMeta to be cloned.
            - new_name (str): The new name for the cloned PluginMeta.

        :returns: A JsonResponse containing the serialized data of the newly cloned PluginMeta if successful, or an error message if the cloning fails.
        :rtype: JsonResponse
        """
        chatbot_id = kwargs.get("chatbot_id")
        new_name = kwargs.get("new_name")
        chatbot: PluginMeta

        if not chatbot_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters. chatbot_id: %s, new_name: %s",
                self.formatted_class_name,
                chatbot_id,
                new_name,
            )
            return JsonResponse({"error": "chatbot_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            chatbot = PluginMeta.objects.with_read_permission_for(self.user_profile.user).get(id=chatbot_id)  # type: ignore
        except PluginMeta.DoesNotExist:
            logger.warning(
                "%s.post() PluginMeta with id %s not found for cloning.", self.formatted_class_name, chatbot_id
            )
            return JsonResponse({"error": f"PluginMeta with id {chatbot_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            cloned_chatbot = chatbot.clone(new_name=new_name, user_profile=self.user_profile)  # type: ignore
            invalidate_all_cached_plugins_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = PluginSerializer(cloned_chatbot).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error cloning PluginMeta with id %s: %s",
                self.formatted_class_name,
                chatbot_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while cloning the PluginMeta: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class PluginListApiDeleteView(SmarterAuthenticatedNeverCachedWebView):
    """
    Delete a plugin for the authenticated user.
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to delete an existing PluginMeta. Validates input
        parameters, checks for the existence of the PluginMeta to be deleted, and
        deletes the PluginMeta if it exists. Invalidates the cache for the user's
        ChatBots after deletion.

        :param request: The HTTP request object containing the parameters for deletion.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - chatbot_id (str): The ID of the PluginMeta to be deleted.

        :returns: A JsonResponse indicating the success or failure of the deletion.
        :rtype: JsonResponse
        """
        chatbot_id = kwargs.get("chatbot_id")
        if not chatbot_id:
            logger.warning("%s.post() Missing required parameter chatbot_id for deletion.", self.formatted_class_name)
            return JsonResponse({"error": "chatbot_id is required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            chatbot = PluginMeta.objects.with_ownership_permission_for(self.user_profile.user).get(id=chatbot_id)  # type: ignore
        except PluginMeta.DoesNotExist:
            logger.warning(
                "%s.post() PluginMeta with id %s not found for deletion.", self.formatted_class_name, chatbot_id
            )
            return JsonResponse({"error": f"PluginMeta with id {chatbot_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            chatbot.delete()
            invalidate_all_cached_plugins_for_user_profile(user_profile=self.user_profile)  # type: ignore
            return JsonResponse(
                {"message": f"PluginMeta with id {chatbot_id} deleted successfully."}, status=HTTPStatus.OK
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error deleting PluginMeta with id %s: %s",
                self.formatted_class_name,
                chatbot_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while deleting the PluginMeta: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class PluginListApiRenameView(SmarterAuthenticatedNeverCachedWebView):
    """
    Rename a plugin for the authenticated user.
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to rename an existing PluginMeta. Validates input
        parameters, checks for the existence of the PluginMeta to be renamed, and
        renames the PluginMeta if it exists. Invalidates the cache for the user's
        ChatBots after renaming.

        :param request: The HTTP request object containing the parameters for renaming.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - chatbot_id (str): The ID of the PluginMeta to be renamed.
            - new_name (str): The new name for the PluginMeta.

        :returns: A JsonResponse indicating the success or failure of the renaming.
        :rtype: JsonResponse
        """
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
            chatbot = PluginMeta.objects.with_ownership_permission_for(self.user_profile.user).get(id=chatbot_id)  # type: ignore
        except PluginMeta.DoesNotExist:
            logger.warning(
                "%s.post() PluginMeta with id %s not found for renaming.", self.formatted_class_name, chatbot_id
            )
            return JsonResponse({"error": f"PluginMeta with id {chatbot_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            chatbot.rename(new_name=new_name)
            invalidate_all_cached_plugins_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = PluginSerializer(chatbot).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error renaming PluginMeta with id %s: %s",
                self.formatted_class_name,
                chatbot_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while renaming the PluginMeta: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )
