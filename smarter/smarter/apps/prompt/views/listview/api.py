# pylint: disable=W0613,C0302
"""
Smarter.apps.prompt.views.listview.api
======================================

Django class-based API views for managing LLMClients in the Smarter workbench web console.

This module provides API endpoints for listing, cloning, deleting, and renaming LLMClients
associated with the authenticated user, as well as any shared LLMClients. All views require
user authentication and leverage caching for responsiveness.

Classes
-------

- PromptListApiView
    Returns a paginated list of LLMClients accessible to the authenticated user, supporting
    filters for owned, shared, or all LLMClients. Supports cache invalidation and pagination.

- PromptListApiCloneView
    API endpoint for cloning an existing LLMClient. Requires the user to provide a new name.

- PromptListApiDeleteView
    API endpoint for deleting a LLMClient owned by the user.

- PromptListApiRenameView
    API endpoint for renaming a LLMClient owned by the user.

Features
--------

- Requires user authentication for all endpoints.
- Supports filtering LLMClients by ownership (owned, shared, or all).
- Provides pagination and cache invalidation options.
- Returns results as JSON responses.
- Uses Django's class-based views and serializers.

Example Endpoints
-----------------

- ``POST /workbench/api/listview/``
- ``POST /workbench/api/listview/all/?page=1&page_size=50&invalidate_cache=false``
- ``POST /workbench/api/listview/owned/?page=1&page_size=25&invalidate_cache=true``
- ``POST /workbench/api/listview/shared/?page=2&page_size=10&invalidate_cache=false``
"""

from http import HTTPStatus

from django.core.paginator import Paginator
from django.db import models
from django.http import HttpRequest
from django.http.response import JsonResponse

from smarter.apps.account.serializers import UserProfileSerializer
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llm_client.caching import (
    get_cached_llm_clients_available_to_user_profile,
    get_cached_llm_clients_owned_by_user_profile,
    get_cached_llm_clients_shared_with_user_profile,
    invalidate_all_cached_llm_clients_for_user_profile,
)
from smarter.apps.llm_client.models import LLMClient
from smarter.apps.llm_client.serializers import LLMClientSerializer
from smarter.common.conf import smarter_settings
from smarter.common.enum import SmarterResourceOwnershipFilterEnum
from smarter.lib import logging
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

DEFAULT_PAGE_SIZE = 25  # default number of llm_clients to return per page in the API response


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING])


def should_log_verbose(level):
    """Check if logging should be done based on the waffle switch."""
    return smarter_settings.verbose_logging


verbose_logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING], condition_func=should_log_verbose
)


class PromptListApiView(SmarterAuthenticatedNeverCachedWebView):
    """
    List API view for the Smarter workbench web console.

    This view returns a paginated list of LLMClients accessible to the authenticated
    user, supporting filters for owned, shared, or all LLMClients. Results are
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
        - Returns paginated LLMClients for the authenticated user.
        - Supports filtering by 'owned', 'shared', or 'all'.
        - Caches results for improved performance.
        - Allows cache invalidation via request.
        - Requires user authentication.

    Attributes:
        DEFAULT_PAGE_SIZE (int): Default number of LLMClients per page.

    Methods:
        post(request, *args, **kwargs):
            Handles POST requests to retrieve LLMClients based on filters and
            pagination.

            Keyword Args:
                ownership_filter (str, optional): 'owned', 'shared', or 'all'.
                    Defaults to 'all'.
                page (int, optional): Page number for pagination. Defaults to 1.
                invalidate_cache (bool, optional): If true, invalidates cache
                    before fetching results. Defaults to False.
                page_size (int, optional): Number of LLMClients per page. Defaults
                    to DEFAULT_PAGE_SIZE.
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{PromptListApiView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to retrieve a list of LLMClients based on ownership filters and pagination.

        The response includes the authenticated user's profile, an admin profile for reference,
        and the list of LLMClients serialized as JSON.

        :param request: The HTTP request object containing query parameters for filtering and pagination.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - ownership_filter (str, optional): Filter for LLMClients based on ownership. Can be 'owned', 'shared', or 'all'. Defaults to 'all'.
            - page (int, optional): Page number for pagination. Defaults to 1.
            - page_size (int, optional): Number of LLMClients to return per page. Defaults to DEFAULT_PAGE_SIZE.
            - invalidate_cache (bool, optional): If true, invalidates the cache for the user's LLMClients before fetching results. Defaults to False.

        :returns: A JsonResponse containing the user's profile, an admin profile, and a list of LLMClients based on the specified filters and pagination.
        :rtype: JsonResponse
        """

        qs: models.QuerySet[LLMClient]
        ownership_filter = kwargs.get("ownership_filter", SmarterResourceOwnershipFilterEnum.ALL)
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

        if invalidate_cache:
            invalidate_all_cached_llm_clients_for_user_profile(user_profile=self.user_profile)  # type: ignore

        if ownership_filter == SmarterResourceOwnershipFilterEnum.OWNED:
            qs = get_cached_llm_clients_owned_by_user_profile(user_profile=self.user_profile)  # type: ignore

        elif ownership_filter == SmarterResourceOwnershipFilterEnum.SHARED:
            qs = get_cached_llm_clients_shared_with_user_profile(user_profile=self.user_profile)  # type: ignore

        elif ownership_filter == SmarterResourceOwnershipFilterEnum.ALL:
            qs = get_cached_llm_clients_available_to_user_profile(user_profile=self.user_profile)  # type: ignore
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
        llm_clients = paginator.get_page(page)

        smarter_admin = smarter_cached_objects.smarter_admin_user_profile
        retval = {
            "user": UserProfileSerializer(self.user_profile).data,
            "admin": UserProfileSerializer(smarter_admin).data,
            "objects": LLMClientSerializer(llm_clients, many=True).data,
        }
        return JsonResponse(retval)


class PromptListApiCloneView(SmarterAuthenticatedNeverCachedWebView):
    """
    API view for cloning a listObject.

    This view is protected and requires the
    user to be authenticated. The user must provide the ID of the listObject to
    clone and a new name for the cloned listObject.

    The view handles POST requests to clone an existing listObject. It validates
    the input parameters, checks for the existence of the listObject to be cloned,
    and creates a new listObject with the specified name. After cloning, it
    invalidates the cache for the user's listObjects to ensure that the new
    listObject appears in subsequent listings.

    Example URL Paths:

        /workbench/api/listview/clone/<int:llm_client_id>/<str:new_name>/
        /workbench/api/listview/clone/123/?new_name=cloned_llm_client/

    :param request: The HTTP request object containing the parameters for cloning.
    :type request: HttpRequest
    :param args: Additional positional arguments (not used).
    :param kwargs: Additional keyword arguments, including:

        - llm_client_id (str): The ID of the LLMClient to be cloned.
        - new_name (str): The new name for the cloned LLMClient.

    :returns: A JsonResponse containing the serialized data of the newly cloned LLMClient if successful, or an error message if the cloning fails.
    :rtype: JsonResponse
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{PromptListApiCloneView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to clone an existing LLMClient.

        Validates input
        parameters, checks for the existence of the LLMClient to be cloned, and
        creates a new LLMClient with the specified name. Invalidates the cache
        for the user's LLMClients after cloning.

        :param request: The HTTP request object containing the parameters for cloning.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - llm_client_id (str): The ID of the LLMClient to be cloned.
            - new_name (str): The new name for the cloned LLMClient.

        :returns: A JsonResponse containing the serialized data of the newly cloned LLMClient if successful, or an error message if the cloning fails.
        :rtype: JsonResponse
        """
        llm_client_id = kwargs.get("llm_client_id")
        new_name = kwargs.get("new_name")
        llm_client: LLMClient

        if not llm_client_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters. llm_client_id: %s, new_name: %s",
                self.formatted_class_name,
                llm_client_id,
                new_name,
            )
            return JsonResponse({"error": "llm_client_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            llm_client = LLMClient.objects.with_read_permission_for(self.user_profile.user).get(id=llm_client_id)  # type: ignore
        except LLMClient.DoesNotExist:
            logger.warning(
                "%s.post() LLMClient with id %s not found for cloning.", self.formatted_class_name, llm_client_id
            )
            return JsonResponse({"error": f"LLMClient with id {llm_client_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            cloned_llm_client = llm_client.clone(new_name=new_name, user_profile=self.user_profile)  # type: ignore
            invalidate_all_cached_llm_clients_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = LLMClientSerializer(cloned_llm_client).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error cloning LLMClient with id %s: %s",
                self.formatted_class_name,
                llm_client_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while cloning the LLMClient: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class PromptListApiDeleteView(SmarterAuthenticatedNeverCachedWebView):
    """
    API view for deleting a LLMClient.

    This view is protected and requires the user to be authenticated.
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{PromptListApiDeleteView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to delete an existing LLMClient.

        Validates input
        parameters, checks for the existence of the LLMClient to be deleted, and
        deletes the LLMClient if it exists. Invalidates the cache for the user's
        LLMClients after deletion.

        :param request: The HTTP request object containing the parameters for deletion.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - llm_client_id (str): The ID of the LLMClient to be deleted.

        :returns: A JsonResponse indicating the success or failure of the deletion.
        :rtype: JsonResponse
        """
        llm_client_id = kwargs.get("llm_client_id")
        if not llm_client_id:
            logger.warning(
                "%s.post() Missing required parameter llm_client_id for deletion.", self.formatted_class_name
            )
            return JsonResponse({"error": "llm_client_id is required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            llm_client = LLMClient.objects.with_ownership_permission_for(self.user_profile.user).get(id=llm_client_id)  # type: ignore
        except LLMClient.DoesNotExist:
            logger.warning(
                "%s.post() LLMClient with id %s not found for deletion.", self.formatted_class_name, llm_client_id
            )
            return JsonResponse({"error": f"LLMClient with id {llm_client_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            llm_client.delete()
            invalidate_all_cached_llm_clients_for_user_profile(user_profile=self.user_profile)  # type: ignore
            return JsonResponse(
                {"message": f"LLMClient with id {llm_client_id} deleted successfully."}, status=HTTPStatus.OK
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error deleting LLMClient with id %s: %s",
                self.formatted_class_name,
                llm_client_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while deleting the LLMClient: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class PromptListApiRenameView(SmarterAuthenticatedNeverCachedWebView):
    """
    API view for renaming a LLMClient.

    This view is protected and requires the user to be authenticated.
    The user must provide the ID of the LLMClient to rename and a new name for the LLMClient.
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{PromptListApiRenameView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to rename an existing LLMClient.

        Validates input parameters, checks for the existence of the LLMClient to be renamed, and
        renames the LLMClient if it exists. Invalidates the cache for the user's
        LLMClients after renaming.

        :param request: The HTTP request object containing the parameters for renaming.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - llm_client_id (str): The ID of the LLMClient to be renamed.
            - new_name (str): The new name for the LLMClient.

        :returns: A JsonResponse indicating the success or failure of the renaming.
        :rtype: JsonResponse
        """
        llm_client_id = kwargs.get("llm_client_id")
        new_name = kwargs.get("new_name")
        if not llm_client_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters for renaming. llm_client_id: %s, new_name: %s",
                self.formatted_class_name,
                llm_client_id,
                new_name,
            )
            return JsonResponse({"error": "llm_client_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            llm_client = LLMClient.objects.with_ownership_permission_for(self.user_profile.user).get(id=llm_client_id)  # type: ignore
        except LLMClient.DoesNotExist:
            logger.warning(
                "%s.post() LLMClient with id %s not found for renaming.", self.formatted_class_name, llm_client_id
            )
            return JsonResponse({"error": f"LLMClient with id {llm_client_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            llm_client.rename(new_name=new_name)
            invalidate_all_cached_llm_clients_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = LLMClientSerializer(llm_client).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error renaming LLMClient with id %s: %s",
                self.formatted_class_name,
                llm_client_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while renaming the LLMClient: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )
