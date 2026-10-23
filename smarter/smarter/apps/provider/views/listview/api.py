# pylint: disable=W0613
"""
This module contains views to implement the React.

Provider list view in the Smarter Dashboard.
"""

from http import HTTPStatus

from django.http import HttpRequest, JsonResponse

from smarter.apps.provider.caching import (
    invalidate_all_cached_providers_for_user_profile,
)
from smarter.apps.provider.models import Provider
from smarter.apps.provider.serializers import ProviderSerializer
from smarter.lib import logging
from smarter.lib.django.listview import SmarterListApiView
from smarter.lib.django.pagination import DEFAULT_SORT_FIELDS
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROVIDER_LOGGING])

SORT_FIELDS = {
    **DEFAULT_SORT_FIELDS,
    "apiKey": "api_key__name",
}
"""The columns of the Provider list that it may be sorted by, and the fields that sort them."""


class ProviderListApiView(SmarterListApiView):
    """
    Render the provider list view for the Smarter Workbench web console.

    This view displays all providers available to the authenticated user as cards, providing a quick overview and access to provider details.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    :returns: Rendered HTML page with a card for each provider, or a 404 error page if the user is not authenticated.
    :rtype: HttpResponse
    """

    model = Provider
    serializer_class = ProviderSerializer
    listview_cache_kind = "Provider"
    sort_fields = SORT_FIELDS
    select_related = ("api_key__user_profile__user", "api_key__user_profile__account", "tos_accepted_by")
    prefetch_related = ("api_key__tags",)


class ProviderListApiCloneView(SmarterAuthenticatedNeverCachedWebView):
    """Clone a provider for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{ProviderListApiCloneView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to clone an existing Provider.

        Validates input
        parameters, checks for the existence of the Provider to be cloned, and
        creates a new Provider with the specified name. Invalidates the cache
        for the user's Providers after cloning.

        :param request: The HTTP request object containing the parameters for cloning.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - provider_id (str): The ID of the Provider to be cloned.
            - new_name (str): The new name for the cloned Provider.

        :returns: A JsonResponse containing the serialized data of the newly cloned Provider if successful, or an error message if the cloning fails.
        :rtype: JsonResponse
        """
        provider_id = kwargs.get("provider_id")
        new_name = kwargs.get("new_name")
        provider: Provider

        if not provider_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters. provider_id: %s, new_name: %s",
                self.formatted_class_name,
                provider_id,
                new_name,
            )
            return JsonResponse({"error": "provider_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            provider = Provider.objects.with_read_permission_for(self.user_profile.user).get(id=provider_id)  # type: ignore
        except Provider.DoesNotExist:
            logger.warning(
                "%s.post() Provider with id %s not found for cloning.", self.formatted_class_name, provider_id
            )
            return JsonResponse({"error": f"Provider with id {provider_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            cloned_provider = provider.clone(new_name=new_name, user_profile=self.user_profile)  # type: ignore
            invalidate_all_cached_providers_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = ProviderSerializer(cloned_provider, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error cloning Provider with id %s: %s",
                self.formatted_class_name,
                provider_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while cloning the Provider: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class ProviderListApiDeleteView(SmarterAuthenticatedNeverCachedWebView):
    """Delete a provider for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{ProviderListApiDeleteView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to delete an existing Provider.

        Validates input
        parameters, checks for the existence of the Provider to be deleted, and
        deletes the Provider if it exists. Invalidates the cache for the user's
        LLMClients after deletion.

        :param request: The HTTP request object containing the parameters for deletion.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - provider_id (str): The ID of the Provider to be deleted.

        :returns: A JsonResponse indicating the success or failure of the deletion.
        :rtype: JsonResponse
        """
        provider_id = kwargs.get("provider_id")
        if not provider_id:
            logger.warning("%s.post() Missing required parameter provider_id for deletion.", self.formatted_class_name)
            return JsonResponse({"error": "provider_id is required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            provider = Provider.objects.with_ownership_permission_for(self.user_profile.user).get(id=provider_id)  # type: ignore
        except Provider.DoesNotExist:
            logger.warning(
                "%s.post() Provider with id %s not found for deletion.", self.formatted_class_name, provider_id
            )
            return JsonResponse({"error": f"Provider with id {provider_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            provider.delete()
            invalidate_all_cached_providers_for_user_profile(user_profile=self.user_profile)  # type: ignore
            return JsonResponse(
                {"message": f"Provider with id {provider_id} deleted successfully."}, status=HTTPStatus.OK
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error deleting Provider with id %s: %s",
                self.formatted_class_name,
                provider_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while deleting the Provider: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class ProviderListApiRenameView(SmarterAuthenticatedNeverCachedWebView):
    """Rename a provider for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{ProviderListApiRenameView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to rename an existing Provider.

        Validates input
        parameters, checks for the existence of the Provider to be renamed, and
        renames the Provider if it exists. Invalidates the cache for the user's
        LLMClients after renaming.

        :param request: The HTTP request object containing the parameters for renaming.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - provider_id (str): The ID of the Provider to be renamed.
            - new_name (str): The new name for the Provider.

        :returns: A JsonResponse indicating the success or failure of the renaming.
        :rtype: JsonResponse
        """
        provider_id = kwargs.get("provider_id")
        new_name = kwargs.get("new_name")
        if not provider_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters for renaming. provider_id: %s, new_name: %s",
                self.formatted_class_name,
                provider_id,
                new_name,
            )
            return JsonResponse({"error": "provider_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            provider = Provider.objects.with_ownership_permission_for(self.user_profile.user).get(id=provider_id)  # type: ignore
        except Provider.DoesNotExist:
            logger.warning(
                "%s.post() Provider with id %s not found for renaming.", self.formatted_class_name, provider_id
            )
            return JsonResponse({"error": f"Provider with id {provider_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            provider.rename(new_name=new_name)
            invalidate_all_cached_providers_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = ProviderSerializer(provider, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error renaming Provider with id %s: %s",
                self.formatted_class_name,
                provider_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while renaming the Provider: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )
