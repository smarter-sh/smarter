# pylint: disable=W0613
"""
This module contains views to implement the React.

Guardrail list view in the Smarter Dashboard.
"""

from http import HTTPStatus

from django.http import HttpRequest, JsonResponse

from smarter.apps.guardrail.caching import (
    invalidate_all_cached_guardrails_for_user_profile,
)
from smarter.apps.guardrail.models import Guardrail
from smarter.apps.guardrail.serializers import GuardrailSerializer
from smarter.lib import logging
from smarter.lib.django.listview import SmarterListApiView
from smarter.lib.django.pagination import DEFAULT_SORT_FIELDS
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROVIDER_LOGGING])

SORT_FIELDS = {
    **DEFAULT_SORT_FIELDS,
    "stage": "stage",
    "category": "category",
}
"""The columns of the Guardrail list that it may be sorted by, and the fields that sort them."""


class GuardrailListApiView(SmarterListApiView):
    """
    Render the guardrail list view for the Smarter Workbench web console.

    This view displays all guardrails available to the authenticated user as cards, providing a quick overview and access to guardrail details.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    :returns: Rendered HTML page with a card for each guardrail, or a 404 error page if the user is not authenticated.
    :rtype: HttpResponse
    """

    model = Guardrail
    serializer_class = GuardrailSerializer
    listview_cache_kind = "Guardrail"
    sort_fields = SORT_FIELDS


class GuardrailListApiCloneView(SmarterAuthenticatedNeverCachedWebView):
    """Clone a guardrail for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{GuardrailListApiCloneView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to clone an existing Guardrail.

        Validates input
        parameters, checks for the existence of the Guardrail to be cloned, and
        creates a new Guardrail with the specified name. Invalidates the cache
        for the user's Guardrails after cloning.

        :param request: The HTTP request object containing the parameters for cloning.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - guardrail_id (str): The ID of the Guardrail to be cloned.
            - new_name (str): The new name for the cloned Guardrail.

        :returns: A JsonResponse containing the serialized data of the newly cloned Guardrail if successful, or an error message if the cloning fails.
        :rtype: JsonResponse
        """
        guardrail_id = kwargs.get("guardrail_id")
        new_name = kwargs.get("new_name")
        guardrail: Guardrail

        if not guardrail_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters. guardrail_id: %s, new_name: %s",
                self.formatted_class_name,
                guardrail_id,
                new_name,
            )
            return JsonResponse({"error": "guardrail_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            guardrail = Guardrail.objects.with_read_permission_for(self.user_profile.user).get(id=guardrail_id)  # type: ignore
        except Guardrail.DoesNotExist:
            logger.warning(
                "%s.post() Guardrail with id %s not found for cloning.", self.formatted_class_name, guardrail_id
            )
            return JsonResponse({"error": f"Guardrail with id {guardrail_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            cloned_guardrail = guardrail.clone(new_name=new_name, user_profile=self.user_profile)  # type: ignore
            invalidate_all_cached_guardrails_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = GuardrailSerializer(cloned_guardrail, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error cloning Guardrail with id %s: %s",
                self.formatted_class_name,
                guardrail_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while cloning the Guardrail: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class GuardrailListApiDeleteView(SmarterAuthenticatedNeverCachedWebView):
    """Delete a guardrail for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{GuardrailListApiDeleteView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to delete an existing Guardrail.

        Validates input
        parameters, checks for the existence of the Guardrail to be deleted, and
        deletes the Guardrail if it exists. Invalidates the cache for the user's
        LLMClients after deletion.

        :param request: The HTTP request object containing the parameters for deletion.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - guardrail_id (str): The ID of the Guardrail to be deleted.

        :returns: A JsonResponse indicating the success or failure of the deletion.
        :rtype: JsonResponse
        """
        guardrail_id = kwargs.get("guardrail_id")
        if not guardrail_id:
            logger.warning("%s.post() Missing required parameter guardrail_id for deletion.", self.formatted_class_name)
            return JsonResponse({"error": "guardrail_id is required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            guardrail = Guardrail.objects.with_ownership_permission_for(self.user_profile.user).get(id=guardrail_id)  # type: ignore
        except Guardrail.DoesNotExist:
            logger.warning(
                "%s.post() Guardrail with id %s not found for deletion.", self.formatted_class_name, guardrail_id
            )
            return JsonResponse({"error": f"Guardrail with id {guardrail_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            guardrail.delete()
            invalidate_all_cached_guardrails_for_user_profile(user_profile=self.user_profile)  # type: ignore
            return JsonResponse(
                {"message": f"Guardrail with id {guardrail_id} deleted successfully."}, status=HTTPStatus.OK
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error deleting Guardrail with id %s: %s",
                self.formatted_class_name,
                guardrail_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while deleting the Guardrail: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class GuardrailListApiRenameView(SmarterAuthenticatedNeverCachedWebView):
    """Rename a guardrail for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{GuardrailListApiRenameView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to rename an existing Guardrail.

        Validates input
        parameters, checks for the existence of the Guardrail to be renamed, and
        renames the Guardrail if it exists. Invalidates the cache for the user's
        LLMClients after renaming.

        :param request: The HTTP request object containing the parameters for renaming.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - guardrail_id (str): The ID of the Guardrail to be renamed.
            - new_name (str): The new name for the Guardrail.

        :returns: A JsonResponse indicating the success or failure of the renaming.
        :rtype: JsonResponse
        """
        guardrail_id = kwargs.get("guardrail_id")
        new_name = kwargs.get("new_name")
        if not guardrail_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters for renaming. guardrail_id: %s, new_name: %s",
                self.formatted_class_name,
                guardrail_id,
                new_name,
            )
            return JsonResponse({"error": "guardrail_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            guardrail = Guardrail.objects.with_ownership_permission_for(self.user_profile.user).get(id=guardrail_id)  # type: ignore
        except Guardrail.DoesNotExist:
            logger.warning(
                "%s.post() Guardrail with id %s not found for renaming.", self.formatted_class_name, guardrail_id
            )
            return JsonResponse({"error": f"Guardrail with id {guardrail_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            guardrail.rename(new_name=new_name)
            invalidate_all_cached_guardrails_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = GuardrailSerializer(guardrail, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error renaming Guardrail with id %s: %s",
                self.formatted_class_name,
                guardrail_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while renaming the Guardrail: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )
