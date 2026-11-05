# pylint: disable=W0613
"""The json apis of the web console's React list app of API keys (AuthTokens): list, clone, delete and rename."""

from http import HTTPStatus

from django.http import HttpRequest, JsonResponse

from smarter.lib import logging
from smarter.lib.django.listview import SmarterListApiView
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.caching import (
    invalidate_all_cached_authtokens_for_user_profile,
)
from smarter.lib.drf.models import SmarterAuthToken as AuthToken
from smarter.lib.drf.serializers.authtoken import (
    SmarterAuthTokenSerializer as AuthTokenSerializer,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.SECRET_LOGGING])


class AuthTokenListApiView(SmarterListApiView):
    """
    Return one page of the API keys available to the authenticated user, as json.

    This is the list api of the ``smarter-authtoken-list`` React app. See
    :class:`~smarter.lib.django.listview.SmarterListApiView` for the response and its caching.
    """

    model = AuthToken
    serializer_class = AuthTokenSerializer
    listview_cache_kind = "SmarterAuthToken"


class AuthTokenListApiCloneView(SmarterAuthenticatedNeverCachedWebView):
    """Clone an API key for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """The view's dotted class name and instance id, formatted for log messages."""
        class_name = f"{__name__}.{AuthTokenListApiCloneView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to clone an existing AuthToken.

        Validates the url parameters, checks that the user may read the AuthToken to be cloned,
        and creates a new AuthToken, owned by the user, with the new name in snake_case.
        Invalidates the user's cached AuthTokens after cloning.

        :param request: The HTTP request.
        :param args: Additional positional arguments (not used).
        :param kwargs: The url parameters:

            - ``authtoken_id``: The ``key_id`` of the AuthToken to be cloned.
            - ``new_name``: The new name for the cloned AuthToken.

        :returns: A JsonResponse with the serialized clone, or an error message with status 400
            or 404.
        """
        authtoken_id = kwargs.get("authtoken_id")
        new_name = kwargs.get("new_name")
        authtoken: AuthToken

        if not authtoken_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters. authtoken_id: %s, new_name: %s",
                self.formatted_class_name,
                authtoken_id,
                new_name,
            )
            return JsonResponse({"error": "authtoken_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            authtoken = AuthToken.objects.with_read_permission_for(self.user_profile.user).get(key_id=authtoken_id)  # type: ignore
        except AuthToken.DoesNotExist:
            logger.warning(
                "%s.post() AuthToken with id %s not found for cloning.", self.formatted_class_name, authtoken_id
            )
            return JsonResponse({"error": f"AuthToken with id {authtoken_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            cloned_authtoken = authtoken.clone(new_name=new_name, user_profile=self.user_profile)  # type: ignore
            invalidate_all_cached_authtokens_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = AuthTokenSerializer(cloned_authtoken, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error cloning AuthToken with id %s: %s",
                self.formatted_class_name,
                authtoken_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while cloning the AuthToken: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class AuthTokenListApiDeleteView(SmarterAuthenticatedNeverCachedWebView):
    """Delete an API key of the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """The view's dotted class name and instance id, formatted for log messages."""
        class_name = f"{__name__}.{AuthTokenListApiDeleteView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to delete an existing AuthToken.

        Validates the url parameter, checks that the user owns the AuthToken to be deleted,
        and deletes it. Invalidates the user's cached AuthTokens after deletion.

        :param request: The HTTP request.
        :param args: Additional positional arguments (not used).
        :param kwargs: The url parameters:

            - ``authtoken_id``: The ``key_id`` of the AuthToken to be deleted.

        :returns: A JsonResponse indicating the success or failure of the deletion.
        """
        authtoken_id = kwargs.get("authtoken_id")
        if not authtoken_id:
            logger.warning("%s.post() Missing required parameter authtoken_id for deletion.", self.formatted_class_name)
            return JsonResponse({"error": "authtoken_id is required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            authtoken = AuthToken.objects.with_ownership_permission_for(self.user_profile.user).get(key_id=authtoken_id)  # type: ignore
        except AuthToken.DoesNotExist:
            logger.warning(
                "%s.post() AuthToken with id %s not found for deletion.", self.formatted_class_name, authtoken_id
            )
            return JsonResponse({"error": f"AuthToken with id {authtoken_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            authtoken.delete()
            invalidate_all_cached_authtokens_for_user_profile(user_profile=self.user_profile)  # type: ignore
            return JsonResponse(
                {"message": f"AuthToken with id {authtoken_id} deleted successfully."}, status=HTTPStatus.OK
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error deleting AuthToken with id %s: %s",
                self.formatted_class_name,
                authtoken_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while deleting the AuthToken: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class AuthTokenListApiRenameView(SmarterAuthenticatedNeverCachedWebView):
    """Rename an API key of the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """The view's dotted class name and instance id, formatted for log messages."""
        class_name = f"{__name__}.{AuthTokenListApiRenameView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to rename an existing AuthToken.

        Validates the url parameters, checks that the user owns the AuthToken to be renamed,
        and renames it, with the new name in snake_case. Invalidates the user's cached
        AuthTokens after renaming.

        :param request: The HTTP request.
        :param args: Additional positional arguments (not used).
        :param kwargs: The url parameters:

            - ``authtoken_id``: The ``key_id`` of the AuthToken to be renamed.
            - ``new_name``: The new name for the AuthToken.

        :returns: A JsonResponse with the serialized AuthToken, or an error message with status
            400 or 404.
        """
        authtoken_id = kwargs.get("authtoken_id")
        new_name = kwargs.get("new_name")
        if not authtoken_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters for renaming. authtoken_id: %s, new_name: %s",
                self.formatted_class_name,
                authtoken_id,
                new_name,
            )
            return JsonResponse({"error": "authtoken_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            authtoken = AuthToken.objects.with_ownership_permission_for(self.user_profile.user).get(key_id=authtoken_id)  # type: ignore
        except AuthToken.DoesNotExist:
            logger.warning(
                "%s.post() AuthToken with id %s not found for renaming.", self.formatted_class_name, authtoken_id
            )
            return JsonResponse({"error": f"AuthToken with id {authtoken_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            authtoken.rename(new_name=new_name)
            invalidate_all_cached_authtokens_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = AuthTokenSerializer(authtoken, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error renaming AuthToken with id %s: %s",
                self.formatted_class_name,
                authtoken_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while renaming the AuthToken: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )
