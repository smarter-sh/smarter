# pylint: disable=W0613
"""
This module contains views to implement the React.

Orchestrator list view in the Smarter Dashboard.
"""

from http import HTTPStatus

from django.http import HttpRequest, JsonResponse

from smarter.apps.orchestrator.caching import (
    invalidate_all_cached_orchestrators_for_user_profile,
)
from smarter.apps.orchestrator.models import Orchestrator
from smarter.apps.orchestrator.serializers import OrchestratorSerializer
from smarter.lib import logging
from smarter.lib.django.listview import SmarterListApiView
from smarter.lib.django.pagination import DEFAULT_SORT_FIELDS
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROVIDER_LOGGING])

SORT_FIELDS = {
    **DEFAULT_SORT_FIELDS,
    "isActive": "is_active",
    "strategy": "strategy",
}
"""The columns of the Orchestrator list that it may be sorted by, and the fields that sort them."""


class OrchestratorListApiView(SmarterListApiView):
    """
    Render the orchestrator list view for the Smarter Workbench web console.

    This view displays all orchestrators available to the authenticated user as cards, providing a quick overview and access to orchestrator details.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    :returns: Rendered HTML page with a card for each orchestrator, or a 404 error page if the user is not authenticated.
    :rtype: HttpResponse
    """

    model = Orchestrator
    serializer_class = OrchestratorSerializer
    listview_cache_kind = "Orchestrator"
    sort_fields = SORT_FIELDS


class OrchestratorListApiCloneView(SmarterAuthenticatedNeverCachedWebView):
    """Clone a orchestrator for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{OrchestratorListApiCloneView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to clone an existing Orchestrator.

        Validates input
        parameters, checks for the existence of the Orchestrator to be cloned, and
        creates a new Orchestrator with the specified name. Invalidates the cache
        for the user's Orchestrators after cloning.

        :param request: The HTTP request object containing the parameters for cloning.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - orchestrator_id (str): The ID of the Orchestrator to be cloned.
            - new_name (str): The new name for the cloned Orchestrator.

        :returns: A JsonResponse containing the serialized data of the newly cloned Orchestrator if successful, or an error message if the cloning fails.
        :rtype: JsonResponse
        """
        orchestrator_id = kwargs.get("orchestrator_id")
        new_name = kwargs.get("new_name")
        orchestrator: Orchestrator

        if not orchestrator_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters. orchestrator_id: %s, new_name: %s",
                self.formatted_class_name,
                orchestrator_id,
                new_name,
            )
            return JsonResponse({"error": "orchestrator_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            orchestrator = Orchestrator.objects.with_read_permission_for(self.user_profile.user).get(id=orchestrator_id)  # type: ignore
        except Orchestrator.DoesNotExist:
            logger.warning(
                "%s.post() Orchestrator with id %s not found for cloning.", self.formatted_class_name, orchestrator_id
            )
            return JsonResponse(
                {"error": f"Orchestrator with id {orchestrator_id} not found."}, status=HTTPStatus.NOT_FOUND
            )

        try:
            new_name = self.to_snake_case(new_name.strip())
            cloned_orchestrator = orchestrator.clone(new_name=new_name, user_profile=self.user_profile)  # type: ignore
            invalidate_all_cached_orchestrators_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = OrchestratorSerializer(cloned_orchestrator, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error cloning Orchestrator with id %s: %s",
                self.formatted_class_name,
                orchestrator_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while cloning the Orchestrator: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class OrchestratorListApiDeleteView(SmarterAuthenticatedNeverCachedWebView):
    """Delete a orchestrator for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{OrchestratorListApiDeleteView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to delete an existing Orchestrator.

        Validates input
        parameters, checks for the existence of the Orchestrator to be deleted, and
        deletes the Orchestrator if it exists. Invalidates the cache for the user's
        LLMClients after deletion.

        :param request: The HTTP request object containing the parameters for deletion.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - orchestrator_id (str): The ID of the Orchestrator to be deleted.

        :returns: A JsonResponse indicating the success or failure of the deletion.
        :rtype: JsonResponse
        """
        orchestrator_id = kwargs.get("orchestrator_id")
        if not orchestrator_id:
            logger.warning(
                "%s.post() Missing required parameter orchestrator_id for deletion.", self.formatted_class_name
            )
            return JsonResponse({"error": "orchestrator_id is required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            orchestrator = Orchestrator.objects.with_ownership_permission_for(self.user_profile.user).get(id=orchestrator_id)  # type: ignore
        except Orchestrator.DoesNotExist:
            logger.warning(
                "%s.post() Orchestrator with id %s not found for deletion.", self.formatted_class_name, orchestrator_id
            )
            return JsonResponse(
                {"error": f"Orchestrator with id {orchestrator_id} not found."}, status=HTTPStatus.NOT_FOUND
            )

        try:
            orchestrator.delete()
            invalidate_all_cached_orchestrators_for_user_profile(user_profile=self.user_profile)  # type: ignore
            return JsonResponse(
                {"message": f"Orchestrator with id {orchestrator_id} deleted successfully."}, status=HTTPStatus.OK
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error deleting Orchestrator with id %s: %s",
                self.formatted_class_name,
                orchestrator_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while deleting the Orchestrator: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class OrchestratorListApiRenameView(SmarterAuthenticatedNeverCachedWebView):
    """Rename a orchestrator for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{OrchestratorListApiRenameView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to rename an existing Orchestrator.

        Validates input
        parameters, checks for the existence of the Orchestrator to be renamed, and
        renames the Orchestrator if it exists. Invalidates the cache for the user's
        LLMClients after renaming.

        :param request: The HTTP request object containing the parameters for renaming.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - orchestrator_id (str): The ID of the Orchestrator to be renamed.
            - new_name (str): The new name for the Orchestrator.

        :returns: A JsonResponse indicating the success or failure of the renaming.
        :rtype: JsonResponse
        """
        orchestrator_id = kwargs.get("orchestrator_id")
        new_name = kwargs.get("new_name")
        if not orchestrator_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters for renaming. orchestrator_id: %s, new_name: %s",
                self.formatted_class_name,
                orchestrator_id,
                new_name,
            )
            return JsonResponse({"error": "orchestrator_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            orchestrator = Orchestrator.objects.with_ownership_permission_for(self.user_profile.user).get(id=orchestrator_id)  # type: ignore
        except Orchestrator.DoesNotExist:
            logger.warning(
                "%s.post() Orchestrator with id %s not found for renaming.", self.formatted_class_name, orchestrator_id
            )
            return JsonResponse(
                {"error": f"Orchestrator with id {orchestrator_id} not found."}, status=HTTPStatus.NOT_FOUND
            )

        try:
            new_name = self.to_snake_case(new_name.strip())
            orchestrator.rename(new_name=new_name)
            invalidate_all_cached_orchestrators_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = OrchestratorSerializer(orchestrator, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error renaming Orchestrator with id %s: %s",
                self.formatted_class_name,
                orchestrator_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while renaming the Orchestrator: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )
