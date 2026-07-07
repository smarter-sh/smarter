# pylint: disable=W0613
"""
This module contains views to implement the React.

MCPClient list view in the Smarter Dashboard.
"""

from http import HTTPStatus
from typing import Union

from django.core.handlers.asgi import ASGIRequest
from django.core.paginator import Paginator
from django.db import models
from django.http import HttpRequest, JsonResponse

from smarter.apps.account.serializers import UserProfileSerializer
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.mcpclient.caching import (
    get_cached_mcpclients_available_to_user_profile,
    get_cached_mcpclients_owned_by_user_profile,
    get_cached_mcpclients_shared_with_user_profile,
    invalidate_all_cached_mcpclients_for_user_profile,
)
from smarter.apps.mcpclient.models import MCPClient
from smarter.apps.mcpclient.serializers import MCPClientSerializer
from smarter.common.enum import SmarterResourceOwnershipFilterEnum
from smarter.lib import logging
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
)
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

DEFAULT_PAGE_SIZE = 25

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROVIDER_LOGGING])


class MCPClientListApiView(SmarterAuthenticatedNeverCachedWebView):
    """
    Render the mcpclient list view for the Smarter Workbench web console.

    This view displays all mcpclients available to the authenticated user as cards, providing a quick overview and access to mcpclient details.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    :returns: Rendered HTML page with a card for each mcpclient, or a 404 error page if the user is not authenticated.
    :rtype: HttpResponse
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{MCPClientListApiView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: ASGIRequest, *args, **kwargs) -> Union[JsonResponse, SmarterHttpResponseNotFound]:
        qs: models.QuerySet[MCPClient]
        ownership_filter = kwargs.get("ownership_filter", SmarterResourceOwnershipFilterEnum.ALL)
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", DEFAULT_PAGE_SIZE)
        invalidate_cache = request.GET.get("invalidate_cache", "false").lower() == "true"

        logger.debug(
            "%s.post() Rendering mcpclient list view for user %s with args=%s, kwargs=%s.",
            self.formatted_class_name,
            request.user.username if request.user else "None",  # type: ignore[union-attr]
            args,
            kwargs,
        )
        if invalidate_cache:
            invalidate_all_cached_mcpclients_for_user_profile(user_profile=self.user_profile)  # type: ignore

        if ownership_filter == SmarterResourceOwnershipFilterEnum.OWNED:
            qs = get_cached_mcpclients_owned_by_user_profile(user_profile=self.user_profile)  # type: ignore

        elif ownership_filter == SmarterResourceOwnershipFilterEnum.SHARED:
            qs = get_cached_mcpclients_shared_with_user_profile(user_profile=self.user_profile)  # type: ignore

        elif ownership_filter == SmarterResourceOwnershipFilterEnum.ALL:
            qs = get_cached_mcpclients_available_to_user_profile(user_profile=self.user_profile)  # type: ignore
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
        mcpclients = paginator.get_page(page)

        smarter_admin = smarter_cached_objects.smarter_admin_user_profile
        retval = {
            "user": UserProfileSerializer(self.user_profile).data,
            "admin": UserProfileSerializer(smarter_admin).data,
            "objects": MCPClientSerializer(mcpclients, many=True).data,
        }
        return JsonResponse(retval)


class MCPClientListApiCloneView(SmarterAuthenticatedNeverCachedWebView):
    """Clone a mcpclient for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{MCPClientListApiCloneView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to clone an existing MCPClient.

        Validates input
        parameters, checks for the existence of the MCPClient to be cloned, and
        creates a new MCPClient with the specified name. Invalidates the cache
        for the user's MCPClients after cloning.

        :param request: The HTTP request object containing the parameters for cloning.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - mcpclient_id (str): The ID of the MCPClient to be cloned.
            - new_name (str): The new name for the cloned MCPClient.

        :returns: A JsonResponse containing the serialized data of the newly cloned MCPClient if successful, or an error message if the cloning fails.
        :rtype: JsonResponse
        """
        mcpclient_id = kwargs.get("mcpclient_id")
        new_name = kwargs.get("new_name")
        mcpclient: MCPClient

        if not mcpclient_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters. mcpclient_id: %s, new_name: %s",
                self.formatted_class_name,
                mcpclient_id,
                new_name,
            )
            return JsonResponse({"error": "mcpclient_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            mcpclient = MCPClient.objects.with_read_permission_for(self.user_profile.user).get(id=mcpclient_id)  # type: ignore
        except MCPClient.DoesNotExist:
            logger.warning(
                "%s.post() MCPClient with id %s not found for cloning.", self.formatted_class_name, mcpclient_id
            )
            return JsonResponse({"error": f"MCPClient with id {mcpclient_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            cloned_mcpclient = mcpclient.clone(new_name=new_name, user_profile=self.user_profile)  # type: ignore
            invalidate_all_cached_mcpclients_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = MCPClientSerializer(cloned_mcpclient).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error cloning MCPClient with id %s: %s",
                self.formatted_class_name,
                mcpclient_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while cloning the MCPClient: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class MCPClientListApiDeleteView(SmarterAuthenticatedNeverCachedWebView):
    """Delete a mcpclient for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{MCPClientListApiDeleteView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to delete an existing MCPClient.

        Validates input
        parameters, checks for the existence of the MCPClient to be deleted, and
        deletes the MCPClient if it exists. Invalidates the cache for the user's
        LLMClients after deletion.

        :param request: The HTTP request object containing the parameters for deletion.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - mcpclient_id (str): The ID of the MCPClient to be deleted.

        :returns: A JsonResponse indicating the success or failure of the deletion.
        :rtype: JsonResponse
        """
        mcpclient_id = kwargs.get("mcpclient_id")
        if not mcpclient_id:
            logger.warning("%s.post() Missing required parameter mcpclient_id for deletion.", self.formatted_class_name)
            return JsonResponse({"error": "mcpclient_id is required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            mcpclient = MCPClient.objects.with_ownership_permission_for(self.user_profile.user).get(id=mcpclient_id)  # type: ignore
        except MCPClient.DoesNotExist:
            logger.warning(
                "%s.post() MCPClient with id %s not found for deletion.", self.formatted_class_name, mcpclient_id
            )
            return JsonResponse({"error": f"MCPClient with id {mcpclient_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            mcpclient.delete()
            invalidate_all_cached_mcpclients_for_user_profile(user_profile=self.user_profile)  # type: ignore
            return JsonResponse(
                {"message": f"MCPClient with id {mcpclient_id} deleted successfully."}, status=HTTPStatus.OK
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error deleting MCPClient with id %s: %s",
                self.formatted_class_name,
                mcpclient_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while deleting the MCPClient: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class MCPClientListApiRenameView(SmarterAuthenticatedNeverCachedWebView):
    """Rename a mcpclient for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{MCPClientListApiRenameView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to rename an existing MCPClient.

        Validates input
        parameters, checks for the existence of the MCPClient to be renamed, and
        renames the MCPClient if it exists. Invalidates the cache for the user's
        LLMClients after renaming.

        :param request: The HTTP request object containing the parameters for renaming.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - mcpclient_id (str): The ID of the MCPClient to be renamed.
            - new_name (str): The new name for the MCPClient.

        :returns: A JsonResponse indicating the success or failure of the renaming.
        :rtype: JsonResponse
        """
        mcpclient_id = kwargs.get("mcpclient_id")
        new_name = kwargs.get("new_name")
        if not mcpclient_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters for renaming. mcpclient_id: %s, new_name: %s",
                self.formatted_class_name,
                mcpclient_id,
                new_name,
            )
            return JsonResponse({"error": "mcpclient_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            mcpclient = MCPClient.objects.with_ownership_permission_for(self.user_profile.user).get(id=mcpclient_id)  # type: ignore
        except MCPClient.DoesNotExist:
            logger.warning(
                "%s.post() MCPClient with id %s not found for renaming.", self.formatted_class_name, mcpclient_id
            )
            return JsonResponse({"error": f"MCPClient with id {mcpclient_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            mcpclient.rename(new_name=new_name)
            invalidate_all_cached_mcpclients_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = MCPClientSerializer(mcpclient).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error renaming MCPClient with id %s: %s",
                self.formatted_class_name,
                mcpclient_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while renaming the MCPClient: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )
