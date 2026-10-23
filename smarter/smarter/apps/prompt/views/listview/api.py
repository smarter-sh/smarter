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
- Provides pagination, search, sorting and cache invalidation options.
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

from django.db.models import Q
from django.http import HttpRequest
from django.http.response import JsonResponse

from smarter.apps.llmclient.caching import (
    invalidate_all_cached_llmclients_for_user_profile,
)
from smarter.apps.llmclient.const import LLMCLIENT_LISTVIEW_CACHE_KIND
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.serializers import LLMClientSerializer
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.listview import SmarterListApiView
from smarter.lib.django.pagination import DEFAULT_SORT_FIELDS
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING])

SORT_FIELDS = {
    **DEFAULT_SORT_FIELDS,
    "provider": "provider",
    "defaultModel": "default_model",
}
"""The columns of the LLMClient list that it may be sorted by, and the fields that sort them."""

PENDING_FILTER = "pending"
"""The name of the filter of the LLMClients that aren't deployed yet."""

FILTERS = {
    PENDING_FILTER: Q(deployed=False),
}
"""The named filters of the LLMClient list.

``?filter=pending`` lists the LLMClients that aren't deployed yet, which the dashboard's pending
deployments link opens.
"""


def should_log_verbose(level):
    """Check if logging should be done based on the waffle switch."""
    return smarter_settings.verbose_logging


verbose_logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING], condition_func=should_log_verbose
)


class PromptListApiView(SmarterListApiView):
    """
    List API view of the LLMClients, for the Smarter workbench web console.

    It returns a page of the LLMClients that the authenticated user owns, that are shared with
    them, or both, cached per user. See :class:`~smarter.lib.django.listview.SmarterListApiView`.

    Example URL Paths:
        /workbench/api/listview/
        /workbench/api/listview/all/?page=1&page_size=50&invalidate_cache=false
        /workbench/api/listview/owned/?page=1&page_size=25&invalidate_cache=true
        /workbench/api/listview/shared/?page=2&page_size=10&search=support&ordering=-name
        /workbench/api/listview/all/?filter=pending
    """

    model = LLMClient
    serializer_class = LLMClientSerializer
    listview_cache_kind = LLMCLIENT_LISTVIEW_CACHE_KIND
    sort_fields = SORT_FIELDS
    filters = FILTERS
    select_related = ("custom_domain",)
    prefetch_related = (
        "llmclientextensions_set__extension",
        "llmclientplugin_set__plugin_meta",
        "llmclientmcpclients_set__mcpclient",
        "llmclientguardrails_set__guardrail",
        "llmclientapikey_set__api_key",
    )


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

        /workbench/api/listview/clone/<int:llmclient_id>/<str:new_name>/
        /workbench/api/listview/clone/123/?new_name=cloned_llmclient/

    :param request: The HTTP request object containing the parameters for cloning.
    :type request: HttpRequest
    :param args: Additional positional arguments (not used).
    :param kwargs: Additional keyword arguments, including:

        - llmclient_id (str): The ID of the LLMClient to be cloned.
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

            - llmclient_id (str): The ID of the LLMClient to be cloned.
            - new_name (str): The new name for the cloned LLMClient.

        :returns: A JsonResponse containing the serialized data of the newly cloned LLMClient if successful, or an error message if the cloning fails.
        :rtype: JsonResponse
        """
        llmclient_id = kwargs.get("llmclient_id")
        new_name = kwargs.get("new_name")
        llmclient: LLMClient

        if not llmclient_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters. llmclient_id: %s, new_name: %s",
                self.formatted_class_name,
                llmclient_id,
                new_name,
            )
            return JsonResponse({"error": "llmclient_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            llmclient = LLMClient.objects.with_read_permission_for(self.user_profile.user).get(id=llmclient_id)  # type: ignore
        except LLMClient.DoesNotExist:
            logger.warning(
                "%s.post() LLMClient with id %s not found for cloning.", self.formatted_class_name, llmclient_id
            )
            return JsonResponse({"error": f"LLMClient with id {llmclient_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            cloned_llmclient = llmclient.clone(new_name=new_name, user_profile=self.user_profile)  # type: ignore
            invalidate_all_cached_llmclients_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = LLMClientSerializer(cloned_llmclient, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error cloning LLMClient with id %s: %s",
                self.formatted_class_name,
                llmclient_id,
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

            - llmclient_id (str): The ID of the LLMClient to be deleted.

        :returns: A JsonResponse indicating the success or failure of the deletion.
        :rtype: JsonResponse
        """
        llmclient_id = kwargs.get("llmclient_id")
        if not llmclient_id:
            logger.warning("%s.post() Missing required parameter llmclient_id for deletion.", self.formatted_class_name)
            return JsonResponse({"error": "llmclient_id is required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            llmclient = LLMClient.objects.with_ownership_permission_for(self.user_profile.user).get(id=llmclient_id)  # type: ignore
        except LLMClient.DoesNotExist:
            logger.warning(
                "%s.post() LLMClient with id %s not found for deletion.", self.formatted_class_name, llmclient_id
            )
            return JsonResponse({"error": f"LLMClient with id {llmclient_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            llmclient.delete()
            invalidate_all_cached_llmclients_for_user_profile(user_profile=self.user_profile)  # type: ignore
            return JsonResponse(
                {"message": f"LLMClient with id {llmclient_id} deleted successfully."}, status=HTTPStatus.OK
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error deleting LLMClient with id %s: %s",
                self.formatted_class_name,
                llmclient_id,
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

            - llmclient_id (str): The ID of the LLMClient to be renamed.
            - new_name (str): The new name for the LLMClient.

        :returns: A JsonResponse indicating the success or failure of the renaming.
        :rtype: JsonResponse
        """
        llmclient_id = kwargs.get("llmclient_id")
        new_name = kwargs.get("new_name")
        if not llmclient_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters for renaming. llmclient_id: %s, new_name: %s",
                self.formatted_class_name,
                llmclient_id,
                new_name,
            )
            return JsonResponse({"error": "llmclient_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            llmclient = LLMClient.objects.with_ownership_permission_for(self.user_profile.user).get(id=llmclient_id)  # type: ignore
        except LLMClient.DoesNotExist:
            logger.warning(
                "%s.post() LLMClient with id %s not found for renaming.", self.formatted_class_name, llmclient_id
            )
            return JsonResponse({"error": f"LLMClient with id {llmclient_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            llmclient.rename(new_name=new_name)
            invalidate_all_cached_llmclients_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = LLMClientSerializer(llmclient, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error renaming LLMClient with id %s: %s",
                self.formatted_class_name,
                llmclient_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while renaming the LLMClient: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )
