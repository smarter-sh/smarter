# pylint: disable=W0613
"""
This module contains views to implement the React.

Secret list view in the Smarter Dashboard.
"""

from http import HTTPStatus
from typing import Union

from django.core.handlers.asgi import ASGIRequest
from django.core.paginator import Paginator
from django.db import models
from django.http import HttpRequest, JsonResponse

from smarter.apps.account.serializers import UserProfileSerializer
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.secret.caching import (
    get_cached_secrets_available_to_user_profile,
    get_cached_secrets_owned_by_user_profile,
    get_cached_secrets_shared_with_user_profile,
    invalidate_all_cached_secrets_for_user_profile,
)
from smarter.apps.secret.models import Secret
from smarter.apps.secret.serializers import SecretSerializer
from smarter.common.enum import SmarterResourceOwnershipFilterEnum
from smarter.lib import logging
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
)
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

DEFAULT_PAGE_SIZE = 25

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.SECRET_LOGGING])


class SecretListApiView(SmarterAuthenticatedNeverCachedWebView):
    """
    Render the secret list view for the Smarter Workbench web console.

    This view displays all secrets available to the authenticated user as cards, providing a quick overview and access to secret details.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    :returns: Rendered HTML page with a card for each secret, or a 404 error page if the user is not authenticated.
    :rtype: HttpResponse
    """

    def post(self, request: ASGIRequest, *args, **kwargs) -> Union[JsonResponse, SmarterHttpResponseNotFound]:
        qs: models.QuerySet[Secret]
        ownership_filter = kwargs.get("ownership_filter", SmarterResourceOwnershipFilterEnum.ALL)
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", DEFAULT_PAGE_SIZE)
        invalidate_cache = request.GET.get("invalidate_cache", "false").lower() == "true"

        logger.debug(
            "%s.get() Rendering secret list view for user %s with args=%s, kwargs=%s.",
            self.formatted_class_name,
            request.user.username if request.user else "None",  # type: ignore[union-attr]
            args,
            kwargs,
        )
        if invalidate_cache:
            invalidate_all_cached_secrets_for_user_profile(user_profile=self.user_profile)  # type: ignore

        if ownership_filter == SmarterResourceOwnershipFilterEnum.OWNED:
            qs = get_cached_secrets_owned_by_user_profile(user_profile=self.user_profile)  # type: ignore

        elif ownership_filter == SmarterResourceOwnershipFilterEnum.SHARED:
            qs = get_cached_secrets_shared_with_user_profile(user_profile=self.user_profile)  # type: ignore

        elif ownership_filter == SmarterResourceOwnershipFilterEnum.ALL:
            qs = get_cached_secrets_available_to_user_profile(user_profile=self.user_profile)  # type: ignore
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
        secrets = paginator.get_page(page)

        smarter_admin = smarter_cached_objects.smarter_admin_user_profile
        retval = {
            "user": UserProfileSerializer(self.user_profile).data,
            "admin": UserProfileSerializer(smarter_admin).data,
            "objects": SecretSerializer(secrets, many=True).data,
        }
        return JsonResponse(retval)


class SecretListApiCloneView(SmarterAuthenticatedNeverCachedWebView):
    """Clone a secret for the authenticated user."""

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to clone an existing Secret.

        Validates input
        parameters, checks for the existence of the Secret to be cloned, and
        creates a new Secret with the specified name. Invalidates the cache
        for the user's LLMClients after cloning.

        :param request: The HTTP request object containing the parameters for cloning.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - secret_id (str): The ID of the Secret to be cloned.
            - new_name (str): The new name for the cloned Secret.

        :returns: A JsonResponse containing the serialized data of the newly cloned Secret if successful, or an error message if the cloning fails.
        :rtype: JsonResponse
        """
        secret_id = kwargs.get("secret_id")
        new_name = kwargs.get("new_name")
        secret: Secret

        if not secret_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters. secret_id: %s, new_name: %s",
                self.formatted_class_name,
                secret_id,
                new_name,
            )
            return JsonResponse({"error": "secret_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            secret = Secret.objects.with_read_permission_for(self.user_profile.user).get(id=secret_id)  # type: ignore
        except Secret.DoesNotExist:
            logger.warning("%s.post() Secret with id %s not found for cloning.", self.formatted_class_name, secret_id)
            return JsonResponse({"error": f"Secret with id {secret_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            cloned_secret = secret.clone(new_name=new_name, user_profile=self.user_profile)  # type: ignore
            invalidate_all_cached_secrets_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = SecretSerializer(cloned_secret).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error cloning Secret with id %s: %s",
                self.formatted_class_name,
                secret_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while cloning the Secret: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class SecretListApiDeleteView(SmarterAuthenticatedNeverCachedWebView):
    """Delete a secret for the authenticated user."""

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to delete an existing Secret.

        Validates input
        parameters, checks for the existence of the Secret to be deleted, and
        deletes the Secret if it exists. Invalidates the cache for the user's
        LLMClients after deletion.

        :param request: The HTTP request object containing the parameters for deletion.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - secret_id (str): The ID of the Secret to be deleted.

        :returns: A JsonResponse indicating the success or failure of the deletion.
        :rtype: JsonResponse
        """
        secret_id = kwargs.get("secret_id")
        if not secret_id:
            logger.warning("%s.post() Missing required parameter secret_id for deletion.", self.formatted_class_name)
            return JsonResponse({"error": "secret_id is required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            secret = Secret.objects.with_ownership_permission_for(self.user_profile.user).get(id=secret_id)  # type: ignore
        except Secret.DoesNotExist:
            logger.warning("%s.post() Secret with id %s not found for deletion.", self.formatted_class_name, secret_id)
            return JsonResponse({"error": f"Secret with id {secret_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            secret.delete()
            invalidate_all_cached_secrets_for_user_profile(user_profile=self.user_profile)  # type: ignore
            return JsonResponse({"message": f"Secret with id {secret_id} deleted successfully."}, status=HTTPStatus.OK)
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error deleting Secret with id %s: %s",
                self.formatted_class_name,
                secret_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while deleting the Secret: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class SecretListApiRenameView(SmarterAuthenticatedNeverCachedWebView):
    """Rename a secret for the authenticated user."""

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to rename an existing Secret.

        Validates input
        parameters, checks for the existence of the Secret to be renamed, and
        renames the Secret if it exists. Invalidates the cache for the user's
        LLMClients after renaming.

        :param request: The HTTP request object containing the parameters for renaming.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - secret_id (str): The ID of the Secret to be renamed.
            - new_name (str): The new name for the Secret.

        :returns: A JsonResponse indicating the success or failure of the renaming.
        :rtype: JsonResponse
        """
        secret_id = kwargs.get("secret_id")
        new_name = kwargs.get("new_name")
        if not secret_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters for renaming. secret_id: %s, new_name: %s",
                self.formatted_class_name,
                secret_id,
                new_name,
            )
            return JsonResponse({"error": "secret_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            secret = Secret.objects.with_ownership_permission_for(self.user_profile.user).get(id=secret_id)  # type: ignore
        except Secret.DoesNotExist:
            logger.warning("%s.post() Secret with id %s not found for renaming.", self.formatted_class_name, secret_id)
            return JsonResponse({"error": f"Secret with id {secret_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            secret.rename(new_name=new_name)
            invalidate_all_cached_secrets_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = SecretSerializer(secret).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error renaming Secret with id %s: %s",
                self.formatted_class_name,
                secret_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while renaming the Secret: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )
