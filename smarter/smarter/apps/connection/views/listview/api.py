# pylint: disable=W0613
"""
This module contains views to implement the React.

ConnectionBase list view in the Smarter Dashboard.
"""

from http import HTTPStatus
from typing import Union

from django.core.handlers.asgi import ASGIRequest
from django.core.paginator import Paginator
from django.db import models, transaction
from django.http import HttpRequest, JsonResponse

from smarter.apps.account.serializers import UserProfileSerializer
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.connection.caching import (
    get_cached_connections_available_to_user_profile,
    get_cached_connections_owned_by_user_profile,
    get_cached_connections_shared_with_user_profile,
    invalidate_all_cached_connections_for_user_profile,
)
from smarter.apps.connection.models import ApiConnection, ConnectionBase, SqlConnection
from smarter.apps.connection.serializers import (
    ApiConnectionSerializer,
    ConnectionSerializer,
    SqlConnectionSerializer,
)
from smarter.common.enum import SmarterResourceOwnershipFilterEnum
from smarter.lib import logging
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
)
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

DEFAULT_PAGE_SIZE = 25

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CONNECTION_LOGGING])


class ConnectionListApiView(SmarterAuthenticatedNeverCachedWebView):
    """
    Render the connection list view for the Smarter Workbench web console.

    This view displays all connections available to the authenticated user as cards, providing a quick overview and access to connection details.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    :returns: Rendered HTML page with a card for each connection, or a 404 error page if the user is not authenticated.
    :rtype: HttpResponse
    """

    def get(self, request: ASGIRequest, *args, **kwargs) -> Union[JsonResponse, SmarterHttpResponseNotFound]:
        return self.post(request, *args, **kwargs)

    def post(self, request: ASGIRequest, *args, **kwargs) -> Union[JsonResponse, SmarterHttpResponseNotFound]:
        qs: models.QuerySet[ConnectionBase]
        ownership_filter = kwargs.get("ownership_filter", SmarterResourceOwnershipFilterEnum.ALL)
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", DEFAULT_PAGE_SIZE)
        invalidate_cache = request.GET.get("invalidate_cache", "false").lower() == "true"

        logger.debug(
            "%s.get() Rendering connection list view for user %s with args=%s, kwargs=%s.",
            self.formatted_class_name,
            request.user.username if request.user else "None",  # type: ignore[union-attr]
            args,
            kwargs,
        )
        if invalidate_cache:
            invalidate_all_cached_connections_for_user_profile(user_profile=self.user_profile)  # type: ignore

        if ownership_filter == SmarterResourceOwnershipFilterEnum.OWNED:
            qs = get_cached_connections_owned_by_user_profile(user_profile=self.user_profile)  # type: ignore

        elif ownership_filter == SmarterResourceOwnershipFilterEnum.SHARED:
            qs = get_cached_connections_shared_with_user_profile(user_profile=self.user_profile)  # type: ignore

        elif ownership_filter == SmarterResourceOwnershipFilterEnum.ALL:
            qs = get_cached_connections_available_to_user_profile(user_profile=self.user_profile)  # type: ignore
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
        connections = paginator.get_page(page)

        smarter_admin = smarter_cached_objects.smarter_admin_user_profile
        retval = {
            "user": UserProfileSerializer(self.user_profile).data,
            "admin": UserProfileSerializer(smarter_admin).data,
            "objects": ConnectionSerializer(connections, many=True).data,
        }
        return JsonResponse(retval)


class ConnectionListApiCloneView(SmarterAuthenticatedNeverCachedWebView):
    """Clone a connection for the authenticated user."""

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to clone an existing ConnectionBase.

        Validates input
        parameters, checks for the existence of the ConnectionBase to be cloned, and
        creates a new ConnectionBase with the specified name. Invalidates the cache
        for the user's LLMClients after cloning.

        :param request: The HTTP request object containing the parameters for cloning.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - connection_id (str): The ID of the ConnectionBase to be cloned.
            - new_name (str): The new name for the cloned ConnectionBase.

        :returns: A JsonResponse containing the serialized data of the newly cloned ConnectionBase if successful, or an error message if the cloning fails.
        :rtype: JsonResponse
        """
        connection_id = kwargs.get("connection_id")
        new_name = kwargs.get("new_name")
        connection: ConnectionBase

        if not connection_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters. connection_id: %s, new_name: %s",
                self.formatted_class_name,
                connection_id,
                new_name,
            )
            return JsonResponse({"error": "connection_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            connection = ConnectionBase.objects.with_read_permission_for(self.user_profile.user).get(id=connection_id)  # type: ignore
        except ConnectionBase.DoesNotExist:
            logger.warning(
                "%s.post() ConnectionBase with id %s not found for cloning.", self.formatted_class_name, connection_id
            )
            return JsonResponse(
                {"error": f"ConnectionBase with id {connection_id} not found."}, status=HTTPStatus.NOT_FOUND
            )

        try:
            new_name = self.to_snake_case(new_name.strip())
            with transaction.atomic():
                connection.clone(new_name=new_name, user_profile=self.user_profile)  # type: ignore
                invalidate_all_cached_connections_for_user_profile(user_profile=self.user_profile)  # type: ignore
                if connection.kind == SAMKinds.SQL_CONNECTION.value:
                    try:
                        sql_connection = SqlConnection.objects.get(id=connection.id)  # type: ignore
                        sql_data = SqlConnectionSerializer(sql_connection).data
                        return JsonResponse(sql_data, status=HTTPStatus.OK)  # type: ignore
                    except SqlConnection.DoesNotExist:
                        logger.error(
                            "%s.post() SqlConnection with id %s not found for cloning.",
                            self.formatted_class_name,
                            connection_id,
                        )
                        return JsonResponse(
                            {"error": f"SqlConnection with id {connection_id} not found."}, status=HTTPStatus.NOT_FOUND
                        )
                elif connection.kind == SAMKinds.API_CONNECTION.value:
                    try:
                        api_connection = ApiConnection.objects.get(id=connection.id)  # type: ignore
                        api_data = ApiConnectionSerializer(api_connection).data
                        return JsonResponse(api_data, status=HTTPStatus.OK)  # type: ignore
                    except ApiConnection.DoesNotExist:
                        logger.error(
                            "%s.post() ApiConnection with id %s not found for cloning.",
                            self.formatted_class_name,
                            connection_id,
                        )
                        return JsonResponse(
                            {"error": f"ApiConnection with id {connection_id} not found."}, status=HTTPStatus.NOT_FOUND
                        )
                else:
                    raise ValueError(f"Unsupported connection kind: {connection.kind}")
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error cloning ConnectionBase with id %s: %s",
                self.formatted_class_name,
                connection_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while cloning the ConnectionBase: {str(e)}"},
                status=HTTPStatus.BAD_REQUEST,
            )


class ConnectionListApiDeleteView(SmarterAuthenticatedNeverCachedWebView):
    """Delete a connection for the authenticated user."""

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to delete an existing ConnectionBase.

        Validates input
        parameters, checks for the existence of the ConnectionBase to be deleted, and
        deletes the ConnectionBase if it exists. Invalidates the cache for the user's
        LLMClients after deletion.

        :param request: The HTTP request object containing the parameters for deletion.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - connection_id (str): The ID of the ConnectionBase to be deleted.

        :returns: A JsonResponse indicating the success or failure of the deletion.
        :rtype: JsonResponse
        """
        connection_id = kwargs.get("connection_id")
        if not connection_id:
            logger.warning(
                "%s.post() Missing required parameter connection_id for deletion.", self.formatted_class_name
            )
            return JsonResponse({"error": "connection_id is required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            connection = ConnectionBase.objects.with_ownership_permission_for(self.user_profile.user).get(id=connection_id)  # type: ignore
        except ConnectionBase.DoesNotExist:
            logger.warning(
                "%s.post() ConnectionBase with id %s not found for deletion.", self.formatted_class_name, connection_id
            )
            return JsonResponse(
                {"error": f"ConnectionBase with id {connection_id} not found."}, status=HTTPStatus.NOT_FOUND
            )

        try:
            connection.delete()
            invalidate_all_cached_connections_for_user_profile(user_profile=self.user_profile)  # type: ignore
            return JsonResponse(
                {"message": f"ConnectionBase with id {connection_id} deleted successfully."}, status=HTTPStatus.OK
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error deleting ConnectionBase with id %s: %s",
                self.formatted_class_name,
                connection_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while deleting the ConnectionBase: {str(e)}"},
                status=HTTPStatus.BAD_REQUEST,
            )


class ConnectionListApiRenameView(SmarterAuthenticatedNeverCachedWebView):
    """Rename a connection for the authenticated user."""

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to rename an existing ConnectionBase.

        Validates input
        parameters, checks for the existence of the ConnectionBase to be renamed, and
        renames the ConnectionBase if it exists. Invalidates the cache for the user's
        LLMClients after renaming.

        :param request: The HTTP request object containing the parameters for renaming.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - connection_id (str): The ID of the ConnectionBase to be renamed.
            - new_name (str): The new name for the ConnectionBase.

        :returns: A JsonResponse indicating the success or failure of the renaming.
        :rtype: JsonResponse
        """
        connection_id = kwargs.get("connection_id")
        new_name = kwargs.get("new_name")
        if not connection_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters for renaming. connection_id: %s, new_name: %s",
                self.formatted_class_name,
                connection_id,
                new_name,
            )
            return JsonResponse({"error": "connection_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            connection = ConnectionBase.objects.with_ownership_permission_for(self.user_profile.user).get(id=connection_id)  # type: ignore
        except ConnectionBase.DoesNotExist:
            logger.warning(
                "%s.post() ConnectionBase with id %s not found for renaming.", self.formatted_class_name, connection_id
            )
            return JsonResponse(
                {"error": f"ConnectionBase with id {connection_id} not found."}, status=HTTPStatus.NOT_FOUND
            )

        try:
            new_name = self.to_snake_case(new_name.strip())
            connection.rename(new_name=new_name)
            invalidate_all_cached_connections_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = ConnectionSerializer(connection).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error renaming ConnectionBase with id %s: %s",
                self.formatted_class_name,
                connection_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while renaming the ConnectionBase: {str(e)}"},
                status=HTTPStatus.BAD_REQUEST,
            )
