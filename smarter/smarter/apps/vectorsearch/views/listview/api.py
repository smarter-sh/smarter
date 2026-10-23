# pylint: disable=W0613
"""
This module contains views to implement the React.

Vectorsearch list view in the Smarter Dashboard.
"""

from http import HTTPStatus

from django.http import HttpRequest, JsonResponse

from smarter.apps.vectorsearch.caching import (
    invalidate_all_cached_vectorsearchs_for_user_profile,
)
from smarter.apps.vectorsearch.models import Vectorsearch
from smarter.apps.vectorsearch.serializers import VectorsearchSerializer
from smarter.lib import logging
from smarter.lib.django.listview import SmarterListApiView
from smarter.lib.django.pagination import DEFAULT_SORT_FIELDS
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROVIDER_LOGGING])

SORT_FIELDS = {
    **DEFAULT_SORT_FIELDS,
    "vectorstore": "vectorstore",
    "searchType": "search_type",
}
"""The columns of the Vectorsearch list that it may be sorted by, and the fields that sort them."""


class VectorsearchListApiView(SmarterListApiView):
    """
    Render the vectorsearch list view for the Smarter Workbench web console.

    This view displays all vectorsearchs available to the authenticated user as cards, providing a quick overview and access to vectorsearch details.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    :returns: Rendered HTML page with a card for each vectorsearch, or a 404 error page if the user is not authenticated.
    :rtype: HttpResponse
    """

    model = Vectorsearch
    serializer_class = VectorsearchSerializer
    listview_cache_kind = "Vectorsearch"
    sort_fields = SORT_FIELDS


class VectorsearchListApiCloneView(SmarterAuthenticatedNeverCachedWebView):
    """Clone a vectorsearch for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{VectorsearchListApiCloneView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to clone an existing Vectorsearch.

        Validates input
        parameters, checks for the existence of the Vectorsearch to be cloned, and
        creates a new Vectorsearch with the specified name. Invalidates the cache
        for the user's Vectorsearchs after cloning.

        :param request: The HTTP request object containing the parameters for cloning.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - vectorsearch_id (str): The ID of the Vectorsearch to be cloned.
            - new_name (str): The new name for the cloned Vectorsearch.

        :returns: A JsonResponse containing the serialized data of the newly cloned Vectorsearch if successful, or an error message if the cloning fails.
        :rtype: JsonResponse
        """
        vectorsearch_id = kwargs.get("vectorsearch_id")
        new_name = kwargs.get("new_name")
        vectorsearch: Vectorsearch

        if not vectorsearch_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters. vectorsearch_id: %s, new_name: %s",
                self.formatted_class_name,
                vectorsearch_id,
                new_name,
            )
            return JsonResponse({"error": "vectorsearch_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            vectorsearch = Vectorsearch.objects.with_read_permission_for(self.user_profile.user).get(id=vectorsearch_id)  # type: ignore
        except Vectorsearch.DoesNotExist:
            logger.warning(
                "%s.post() Vectorsearch with id %s not found for cloning.", self.formatted_class_name, vectorsearch_id
            )
            return JsonResponse(
                {"error": f"Vectorsearch with id {vectorsearch_id} not found."}, status=HTTPStatus.NOT_FOUND
            )

        try:
            new_name = self.to_snake_case(new_name.strip())
            cloned_vectorsearch = vectorsearch.clone(new_name=new_name, user_profile=self.user_profile)  # type: ignore
            invalidate_all_cached_vectorsearchs_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = VectorsearchSerializer(cloned_vectorsearch, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error cloning Vectorsearch with id %s: %s",
                self.formatted_class_name,
                vectorsearch_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while cloning the Vectorsearch: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class VectorsearchListApiDeleteView(SmarterAuthenticatedNeverCachedWebView):
    """Delete a vectorsearch for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{VectorsearchListApiDeleteView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to delete an existing Vectorsearch.

        Validates input
        parameters, checks for the existence of the Vectorsearch to be deleted, and
        deletes the Vectorsearch if it exists. Invalidates the cache for the user's
        LLMClients after deletion.

        :param request: The HTTP request object containing the parameters for deletion.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - vectorsearch_id (str): The ID of the Vectorsearch to be deleted.

        :returns: A JsonResponse indicating the success or failure of the deletion.
        :rtype: JsonResponse
        """
        vectorsearch_id = kwargs.get("vectorsearch_id")
        if not vectorsearch_id:
            logger.warning(
                "%s.post() Missing required parameter vectorsearch_id for deletion.", self.formatted_class_name
            )
            return JsonResponse({"error": "vectorsearch_id is required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            vectorsearch = Vectorsearch.objects.with_ownership_permission_for(self.user_profile.user).get(id=vectorsearch_id)  # type: ignore
        except Vectorsearch.DoesNotExist:
            logger.warning(
                "%s.post() Vectorsearch with id %s not found for deletion.", self.formatted_class_name, vectorsearch_id
            )
            return JsonResponse(
                {"error": f"Vectorsearch with id {vectorsearch_id} not found."}, status=HTTPStatus.NOT_FOUND
            )

        try:
            vectorsearch.delete()
            invalidate_all_cached_vectorsearchs_for_user_profile(user_profile=self.user_profile)  # type: ignore
            return JsonResponse(
                {"message": f"Vectorsearch with id {vectorsearch_id} deleted successfully."}, status=HTTPStatus.OK
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error deleting Vectorsearch with id %s: %s",
                self.formatted_class_name,
                vectorsearch_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while deleting the Vectorsearch: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class VectorsearchListApiRenameView(SmarterAuthenticatedNeverCachedWebView):
    """Rename a vectorsearch for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{VectorsearchListApiRenameView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to rename an existing Vectorsearch.

        Validates input
        parameters, checks for the existence of the Vectorsearch to be renamed, and
        renames the Vectorsearch if it exists. Invalidates the cache for the user's
        LLMClients after renaming.

        :param request: The HTTP request object containing the parameters for renaming.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - vectorsearch_id (str): The ID of the Vectorsearch to be renamed.
            - new_name (str): The new name for the Vectorsearch.

        :returns: A JsonResponse indicating the success or failure of the renaming.
        :rtype: JsonResponse
        """
        vectorsearch_id = kwargs.get("vectorsearch_id")
        new_name = kwargs.get("new_name")
        if not vectorsearch_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters for renaming. vectorsearch_id: %s, new_name: %s",
                self.formatted_class_name,
                vectorsearch_id,
                new_name,
            )
            return JsonResponse({"error": "vectorsearch_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            vectorsearch = Vectorsearch.objects.with_ownership_permission_for(self.user_profile.user).get(id=vectorsearch_id)  # type: ignore
        except Vectorsearch.DoesNotExist:
            logger.warning(
                "%s.post() Vectorsearch with id %s not found for renaming.", self.formatted_class_name, vectorsearch_id
            )
            return JsonResponse(
                {"error": f"Vectorsearch with id {vectorsearch_id} not found."}, status=HTTPStatus.NOT_FOUND
            )

        try:
            new_name = self.to_snake_case(new_name.strip())
            vectorsearch.rename(new_name=new_name)
            invalidate_all_cached_vectorsearchs_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = VectorsearchSerializer(vectorsearch, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error renaming Vectorsearch with id %s: %s",
                self.formatted_class_name,
                vectorsearch_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while renaming the Vectorsearch: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )
