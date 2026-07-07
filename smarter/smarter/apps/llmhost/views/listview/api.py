# pylint: disable=W0613
"""
This module contains views to implement the React.

LLMHost list view in the Smarter Dashboard.
"""

from http import HTTPStatus
from typing import Union

from django.core.handlers.asgi import ASGIRequest
from django.core.paginator import Paginator
from django.db import models
from django.http import HttpRequest, JsonResponse

from smarter.apps.account.serializers import UserProfileSerializer
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmhost.caching import (
    get_cached_llmhosts_available_to_user_profile,
    get_cached_llmhosts_owned_by_user_profile,
    get_cached_llmhosts_shared_with_user_profile,
    invalidate_all_cached_llmhosts_for_user_profile,
)
from smarter.apps.llmhost.models import LLMHost
from smarter.apps.llmhost.serializers import LLMHostSerializer
from smarter.common.enum import SmarterResourceOwnershipFilterEnum
from smarter.lib import logging
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
)
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

DEFAULT_PAGE_SIZE = 25

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROVIDER_LOGGING])


class LLMHostListApiView(SmarterAuthenticatedNeverCachedWebView):
    """
    Render the llmhost list view for the Smarter Workbench web console.

    This view displays all llmhosts available to the authenticated user as cards, providing a quick overview and access to llmhost details.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    :returns: Rendered HTML page with a card for each llmhost, or a 404 error page if the user is not authenticated.
    :rtype: HttpResponse
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{LLMHostListApiView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: ASGIRequest, *args, **kwargs) -> Union[JsonResponse, SmarterHttpResponseNotFound]:
        qs: models.QuerySet[LLMHost]
        ownership_filter = kwargs.get("ownership_filter", SmarterResourceOwnershipFilterEnum.ALL)
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", DEFAULT_PAGE_SIZE)
        invalidate_cache = request.GET.get("invalidate_cache", "false").lower() == "true"

        logger.debug(
            "%s.post() Rendering llmhost list view for user %s with args=%s, kwargs=%s.",
            self.formatted_class_name,
            request.user.username if request.user else "None",  # type: ignore[union-attr]
            args,
            kwargs,
        )
        if invalidate_cache:
            invalidate_all_cached_llmhosts_for_user_profile(user_profile=self.user_profile)  # type: ignore

        if ownership_filter == SmarterResourceOwnershipFilterEnum.OWNED:
            qs = get_cached_llmhosts_owned_by_user_profile(user_profile=self.user_profile)  # type: ignore

        elif ownership_filter == SmarterResourceOwnershipFilterEnum.SHARED:
            qs = get_cached_llmhosts_shared_with_user_profile(user_profile=self.user_profile)  # type: ignore

        elif ownership_filter == SmarterResourceOwnershipFilterEnum.ALL:
            qs = get_cached_llmhosts_available_to_user_profile(user_profile=self.user_profile)  # type: ignore
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
        llmhosts = paginator.get_page(page)

        smarter_admin = smarter_cached_objects.smarter_admin_user_profile
        retval = {
            "user": UserProfileSerializer(self.user_profile).data,
            "admin": UserProfileSerializer(smarter_admin).data,
            "objects": LLMHostSerializer(llmhosts, many=True).data,
        }
        return JsonResponse(retval)


class LLMHostListApiCloneView(SmarterAuthenticatedNeverCachedWebView):
    """Clone a llmhost for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{LLMHostListApiCloneView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to clone an existing LLMHost.

        Validates input
        parameters, checks for the existence of the LLMHost to be cloned, and
        creates a new LLMHost with the specified name. Invalidates the cache
        for the user's LLMHosts after cloning.

        :param request: The HTTP request object containing the parameters for cloning.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - llmhost_id (str): The ID of the LLMHost to be cloned.
            - new_name (str): The new name for the cloned LLMHost.

        :returns: A JsonResponse containing the serialized data of the newly cloned LLMHost if successful, or an error message if the cloning fails.
        :rtype: JsonResponse
        """
        llmhost_id = kwargs.get("llmhost_id")
        new_name = kwargs.get("new_name")
        llmhost: LLMHost

        if not llmhost_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters. llmhost_id: %s, new_name: %s",
                self.formatted_class_name,
                llmhost_id,
                new_name,
            )
            return JsonResponse({"error": "llmhost_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            llmhost = LLMHost.objects.with_read_permission_for(self.user_profile.user).get(id=llmhost_id)  # type: ignore
        except LLMHost.DoesNotExist:
            logger.warning("%s.post() LLMHost with id %s not found for cloning.", self.formatted_class_name, llmhost_id)
            return JsonResponse({"error": f"LLMHost with id {llmhost_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            cloned_llmhost = llmhost.clone(new_name=new_name, user_profile=self.user_profile)  # type: ignore
            invalidate_all_cached_llmhosts_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = LLMHostSerializer(cloned_llmhost).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error cloning LLMHost with id %s: %s",
                self.formatted_class_name,
                llmhost_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while cloning the LLMHost: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class LLMHostListApiDeleteView(SmarterAuthenticatedNeverCachedWebView):
    """Delete a llmhost for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{LLMHostListApiDeleteView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to delete an existing LLMHost.

        Validates input
        parameters, checks for the existence of the LLMHost to be deleted, and
        deletes the LLMHost if it exists. Invalidates the cache for the user's
        LLMClients after deletion.

        :param request: The HTTP request object containing the parameters for deletion.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - llmhost_id (str): The ID of the LLMHost to be deleted.

        :returns: A JsonResponse indicating the success or failure of the deletion.
        :rtype: JsonResponse
        """
        llmhost_id = kwargs.get("llmhost_id")
        if not llmhost_id:
            logger.warning("%s.post() Missing required parameter llmhost_id for deletion.", self.formatted_class_name)
            return JsonResponse({"error": "llmhost_id is required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            llmhost = LLMHost.objects.with_ownership_permission_for(self.user_profile.user).get(id=llmhost_id)  # type: ignore
        except LLMHost.DoesNotExist:
            logger.warning(
                "%s.post() LLMHost with id %s not found for deletion.", self.formatted_class_name, llmhost_id
            )
            return JsonResponse({"error": f"LLMHost with id {llmhost_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            llmhost.delete()
            invalidate_all_cached_llmhosts_for_user_profile(user_profile=self.user_profile)  # type: ignore
            return JsonResponse(
                {"message": f"LLMHost with id {llmhost_id} deleted successfully."}, status=HTTPStatus.OK
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error deleting LLMHost with id %s: %s",
                self.formatted_class_name,
                llmhost_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while deleting the LLMHost: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class LLMHostListApiRenameView(SmarterAuthenticatedNeverCachedWebView):
    """Rename a llmhost for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{LLMHostListApiRenameView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to rename an existing LLMHost.

        Validates input
        parameters, checks for the existence of the LLMHost to be renamed, and
        renames the LLMHost if it exists. Invalidates the cache for the user's
        LLMClients after renaming.

        :param request: The HTTP request object containing the parameters for renaming.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - llmhost_id (str): The ID of the LLMHost to be renamed.
            - new_name (str): The new name for the LLMHost.

        :returns: A JsonResponse indicating the success or failure of the renaming.
        :rtype: JsonResponse
        """
        llmhost_id = kwargs.get("llmhost_id")
        new_name = kwargs.get("new_name")
        if not llmhost_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters for renaming. llmhost_id: %s, new_name: %s",
                self.formatted_class_name,
                llmhost_id,
                new_name,
            )
            return JsonResponse({"error": "llmhost_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            llmhost = LLMHost.objects.with_ownership_permission_for(self.user_profile.user).get(id=llmhost_id)  # type: ignore
        except LLMHost.DoesNotExist:
            logger.warning(
                "%s.post() LLMHost with id %s not found for renaming.", self.formatted_class_name, llmhost_id
            )
            return JsonResponse({"error": f"LLMHost with id {llmhost_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            llmhost.rename(new_name=new_name)
            invalidate_all_cached_llmhosts_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = LLMHostSerializer(llmhost).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error renaming LLMHost with id %s: %s",
                self.formatted_class_name,
                llmhost_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while renaming the LLMHost: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )
