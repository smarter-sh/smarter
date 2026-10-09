# pylint: disable=W0613
"""
This module contains views to implement the React.

LLMHost and LLMHostCompute list views in the Smarter Dashboard.
"""

from http import HTTPStatus
from typing import Union

from django.core.handlers.asgi import ASGIRequest
from django.db import models
from django.http import HttpRequest, JsonResponse

from smarter.apps.account.serializers import UserProfileSerializer
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmhost.caching import (
    get_cached_llmhost_computes_available_to_user_profile,
    get_cached_llmhost_computes_owned_by_user_profile,
    get_cached_llmhost_computes_shared_with_user_profile,
    get_cached_llmhosts_available_to_user_profile,
    get_cached_llmhosts_owned_by_user_profile,
    get_cached_llmhosts_shared_with_user_profile,
    invalidate_all_cached_llmhost_computes_for_user_profile,
    invalidate_all_cached_llmhosts_for_user_profile,
)
from smarter.apps.llmhost.models import LLMHost, LLMHostCompute
from smarter.apps.llmhost.serializers import LLMHostComputeSerializer, LLMHostSerializer
from smarter.common.enum import SmarterResourceOwnershipFilterEnum
from smarter.lib import logging
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
)
from smarter.lib.django.pagination import DEFAULT_SORT_FIELDS, paginate_listview
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_HOST_LOGGING])

SORT_FIELDS = {
    **DEFAULT_SORT_FIELDS,
    "isActive": "is_active",
}
"""The columns of the LLMHost list that it may be sorted by, and the fields that sort them."""

COMPUTE_SORT_FIELDS = {
    **DEFAULT_SORT_FIELDS,
    "instanceType": "instance_type",
    "gpuCount": "gpu_count",
    "cpu": "cpu",
    "pricePerHour": "price_per_hour",
}
"""The columns of the LLMHostCompute list that it may be sorted by, and the fields that sort them."""


class LLMHostListApiView(SmarterAuthenticatedNeverCachedWebView):
    """
    Render the llmhost list view for the Smarter Workbench web console.

    This view displays all llmhosts available to the authenticated user as cards, providing a quick overview and access to llmhost details.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    :returns: Rendered HTML page with a card for each llmhost, or a 404 error page if the user is not authenticated.
    :rtype: HttpResponse
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{LLMHostListApiView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: ASGIRequest, *args, **kwargs) -> Union[JsonResponse, SmarterHttpResponseNotFound]:
        qs: models.QuerySet[LLMHost]
        ownership_filter = kwargs.get("ownership_filter", SmarterResourceOwnershipFilterEnum.ALL)
        invalidate_cache = request.GET.get("invalidate_cache", "false").lower() == "true"

        logger.debug(
            "%s.post() Rendering llmhost list view for user %s with args=%s, kwargs=%s.",
            self.formatted_class_name,
            request.user.username if request.user else "None",  # type: ignore[union-attr]
            args,
            kwargs,
        )
        if invalidate_cache:
            invalidate_all_cached_llmhosts_for_user_profile(user_profile=self.user_profile)  # type: ignore

        if ownership_filter == SmarterResourceOwnershipFilterEnum.OWNED:
            qs = get_cached_llmhosts_owned_by_user_profile(user_profile=self.user_profile)  # type: ignore

        elif ownership_filter == SmarterResourceOwnershipFilterEnum.SHARED:
            qs = get_cached_llmhosts_shared_with_user_profile(user_profile=self.user_profile)  # type: ignore

        elif ownership_filter == SmarterResourceOwnershipFilterEnum.ALL:
            qs = get_cached_llmhosts_available_to_user_profile(user_profile=self.user_profile)  # type: ignore
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

        llmhosts, pagination = paginate_listview(request, qs.order_by("-updated_at"), sort_fields=SORT_FIELDS)

        smarter_admin = smarter_cached_objects.smarter_admin_user_profile
        retval = {
            "user": UserProfileSerializer(self.user_profile).data,
            "admin": UserProfileSerializer(smarter_admin).data,
            "objects": LLMHostSerializer(llmhosts, many=True, context={"request": request}).data,
            "pagination": pagination,
        }
        return JsonResponse(retval)


class LLMHostListApiCloneView(SmarterAuthenticatedNeverCachedWebView):
    """Clone a llmhost for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{LLMHostListApiCloneView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to clone an existing LLMHost.

        Validates input
        parameters, checks for the existence of the LLMHost to be cloned, and
        creates a new LLMHost with the specified name. Invalidates the cache
        for the user's LLMHosts after cloning.

        :param request: The HTTP request object containing the parameters for cloning.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - llmhost_id (str): The ID of the LLMHost to be cloned.
            - new_name (str): The new name for the cloned LLMHost.

        :returns: A JsonResponse containing the serialized data of the newly cloned LLMHost if successful, or an error message if the cloning fails.
        :rtype: JsonResponse
        """
        llmhost_id = kwargs.get("llmhost_id")
        new_name = kwargs.get("new_name")
        llmhost: LLMHost

        if not llmhost_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters. llmhost_id: %s, new_name: %s",
                self.formatted_class_name,
                llmhost_id,
                new_name,
            )
            return JsonResponse({"error": "llmhost_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            llmhost = LLMHost.objects.with_read_permission_for(self.user_profile.user).get(id=llmhost_id)  # type: ignore
        except LLMHost.DoesNotExist:
            logger.warning("%s.post() LLMHost with id %s not found for cloning.", self.formatted_class_name, llmhost_id)
            return JsonResponse({"error": f"LLMHost with id {llmhost_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            cloned_llmhost = llmhost.clone(new_name=new_name, user_profile=self.user_profile)  # type: ignore
            invalidate_all_cached_llmhosts_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = LLMHostSerializer(cloned_llmhost, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error cloning LLMHost with id %s: %s",
                self.formatted_class_name,
                llmhost_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while cloning the LLMHost: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class LLMHostListApiDeleteView(SmarterAuthenticatedNeverCachedWebView):
    """Delete a llmhost for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{LLMHostListApiDeleteView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to delete an existing LLMHost.

        Validates input
        parameters, checks for the existence of the LLMHost to be deleted, and
        deletes the LLMHost if it exists. Invalidates the cache for the user's
        LLMHosts after deletion.

        :param request: The HTTP request object containing the parameters for deletion.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - llmhost_id (str): The ID of the LLMHost to be deleted.

        :returns: A JsonResponse indicating the success or failure of the deletion.
        :rtype: JsonResponse
        """
        llmhost_id = kwargs.get("llmhost_id")
        if not llmhost_id:
            logger.warning("%s.post() Missing required parameter llmhost_id for deletion.", self.formatted_class_name)
            return JsonResponse({"error": "llmhost_id is required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            llmhost = LLMHost.objects.with_ownership_permission_for(self.user_profile.user).get(id=llmhost_id)  # type: ignore
        except LLMHost.DoesNotExist:
            logger.warning(
                "%s.post() LLMHost with id %s not found for deletion.", self.formatted_class_name, llmhost_id
            )
            return JsonResponse({"error": f"LLMHost with id {llmhost_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            llmhost.delete()
            invalidate_all_cached_llmhosts_for_user_profile(user_profile=self.user_profile)  # type: ignore
            return JsonResponse(
                {"message": f"LLMHost with id {llmhost_id} deleted successfully."}, status=HTTPStatus.OK
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error deleting LLMHost with id %s: %s",
                self.formatted_class_name,
                llmhost_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while deleting the LLMHost: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class LLMHostListApiRenameView(SmarterAuthenticatedNeverCachedWebView):
    """Rename a llmhost for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{LLMHostListApiRenameView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to rename an existing LLMHost.

        Validates input
        parameters, checks for the existence of the LLMHost to be renamed, and
        renames the LLMHost if it exists. Invalidates the cache for the user's
        LLMHosts after renaming.

        :param request: The HTTP request object containing the parameters for renaming.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - llmhost_id (str): The ID of the LLMHost to be renamed.
            - new_name (str): The new name for the LLMHost.

        :returns: A JsonResponse indicating the success or failure of the renaming.
        :rtype: JsonResponse
        """
        llmhost_id = kwargs.get("llmhost_id")
        new_name = kwargs.get("new_name")
        if not llmhost_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters for renaming. llmhost_id: %s, new_name: %s",
                self.formatted_class_name,
                llmhost_id,
                new_name,
            )
            return JsonResponse({"error": "llmhost_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            llmhost = LLMHost.objects.with_ownership_permission_for(self.user_profile.user).get(id=llmhost_id)  # type: ignore
        except LLMHost.DoesNotExist:
            logger.warning(
                "%s.post() LLMHost with id %s not found for renaming.", self.formatted_class_name, llmhost_id
            )
            return JsonResponse({"error": f"LLMHost with id {llmhost_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            llmhost.rename(new_name=new_name)
            invalidate_all_cached_llmhosts_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = LLMHostSerializer(llmhost, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error renaming LLMHost with id %s: %s",
                self.formatted_class_name,
                llmhost_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while renaming the LLMHost: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


# ------------------------------------------------------------------------------
# LLMHostCompute
# ------------------------------------------------------------------------------


class LLMHostComputeListApiView(SmarterAuthenticatedNeverCachedWebView):
    """Return the LLMHostComputes available to the authenticated user, for the React list view in the Smarter Workbench web console: their own, and those shared with them, e.g. the built-in LLMHostComputes, which the Smarter admin owns."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{LLMHostComputeListApiView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: ASGIRequest, *args, **kwargs) -> Union[JsonResponse, SmarterHttpResponseNotFound]:
        qs: models.QuerySet[LLMHostCompute]
        ownership_filter = kwargs.get("ownership_filter", SmarterResourceOwnershipFilterEnum.ALL)
        invalidate_cache = request.GET.get("invalidate_cache", "false").lower() == "true"

        logger.debug(
            "%s.post() Rendering llmhost compute list view for user %s with args=%s, kwargs=%s.",
            self.formatted_class_name,
            request.user.username if request.user else "None",  # type: ignore[union-attr]
            args,
            kwargs,
        )
        if invalidate_cache:
            invalidate_all_cached_llmhost_computes_for_user_profile(user_profile=self.user_profile)  # type: ignore

        if ownership_filter == SmarterResourceOwnershipFilterEnum.OWNED:
            qs = get_cached_llmhost_computes_owned_by_user_profile(user_profile=self.user_profile)  # type: ignore
        elif ownership_filter == SmarterResourceOwnershipFilterEnum.SHARED:
            qs = get_cached_llmhost_computes_shared_with_user_profile(user_profile=self.user_profile)  # type: ignore
        elif ownership_filter == SmarterResourceOwnershipFilterEnum.ALL:
            qs = get_cached_llmhost_computes_available_to_user_profile(user_profile=self.user_profile)  # type: ignore
        else:
            logger.warning(
                "%s.post() Received an invalid ownership_filter value: %s. Must be one of 'owned', 'shared', or 'all'.",
                self.formatted_class_name,
                ownership_filter,
            )
            return JsonResponse(
                {"error": "Invalid ownership_filter. Must be one of 'owned', 'shared', or 'all'."},
                status=HTTPStatus.BAD_REQUEST,
            )

        computes, pagination = paginate_listview(request, qs.order_by("-updated_at"), sort_fields=COMPUTE_SORT_FIELDS)

        smarter_admin = smarter_cached_objects.smarter_admin_user_profile
        retval = {
            "user": UserProfileSerializer(self.user_profile).data,
            "admin": UserProfileSerializer(smarter_admin).data,
            "objects": LLMHostComputeSerializer(computes, many=True, context={"request": request}).data,
            "pagination": pagination,
        }
        return JsonResponse(retval)


class LLMHostComputeListApiCloneView(SmarterAuthenticatedNeverCachedWebView):
    """
    Clone an LLMHostCompute for the authenticated user: its spec, but not its node group, which.

    Smarter creates when an LLMHost first needs one of the clone's nodes.
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{LLMHostComputeListApiCloneView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to clone an LLMHostCompute that the user may read.

        :param kwargs: llmhost_compute_id (str): the LLMHostCompute to clone. new_name (str): the clone's name.
        :returns: The clone, serialized, or an error message.
        :rtype: JsonResponse
        """
        compute_id = kwargs.get("llmhost_compute_id")
        new_name = kwargs.get("new_name")
        if not compute_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters. llmhost_compute_id: %s, new_name: %s",
                self.formatted_class_name,
                compute_id,
                new_name,
            )
            return JsonResponse(
                {"error": "llmhost_compute_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST
            )

        try:
            compute = LLMHostCompute.objects.with_read_permission_for(self.user_profile.user).get(id=compute_id)  # type: ignore
        except LLMHostCompute.DoesNotExist:
            logger.warning("%s.post() LLMHostCompute with id %s not found.", self.formatted_class_name, compute_id)
            return JsonResponse(
                {"error": f"LLMHostCompute with id {compute_id} not found."}, status=HTTPStatus.NOT_FOUND
            )

        try:
            new_name = self.to_snake_case(new_name.strip())
            cloned = compute.clone(new_name=new_name, user_profile=self.user_profile)  # type: ignore
            invalidate_all_cached_llmhost_computes_for_user_profile(user_profile=self.user_profile)  # type: ignore
            return JsonResponse(LLMHostComputeSerializer(cloned, context={"request": request}).data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error cloning LLMHostCompute with id %s: %s",
                self.formatted_class_name,
                compute_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while cloning the LLMHostCompute: {str(e)}"},
                status=HTTPStatus.BAD_REQUEST,
            )


class LLMHostComputeListApiDeleteView(SmarterAuthenticatedNeverCachedWebView):
    """
    Delete an LLMHostCompute that the authenticated user owns, and its node group.

    Refused while
    LLMHosts use it.
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{LLMHostComputeListApiDeleteView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to delete an LLMHostCompute.

        :param kwargs: llmhost_compute_id (str): the LLMHostCompute to delete.
        :returns: A success or error message.
        :rtype: JsonResponse
        """
        compute_id = kwargs.get("llmhost_compute_id")
        if not compute_id:
            logger.warning("%s.post() Missing required parameter llmhost_compute_id.", self.formatted_class_name)
            return JsonResponse({"error": "llmhost_compute_id is required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            compute = LLMHostCompute.objects.with_ownership_permission_for(self.user_profile.user).get(id=compute_id)  # type: ignore
        except LLMHostCompute.DoesNotExist:
            logger.warning("%s.post() LLMHostCompute with id %s not found.", self.formatted_class_name, compute_id)
            return JsonResponse(
                {"error": f"LLMHostCompute with id {compute_id} not found."}, status=HTTPStatus.NOT_FOUND
            )

        names = sorted(compute.llmhosts.values_list("name", flat=True))  # type: ignore[attr-defined]
        if names:
            return JsonResponse(
                {
                    "error": f"LLMHostCompute {compute.name} cannot be deleted while LLMHosts use it: {', '.join(names)}."
                },
                status=HTTPStatus.BAD_REQUEST,
            )

        try:
            # the pre_delete receiver deletes the node group.
            compute.delete()
            invalidate_all_cached_llmhost_computes_for_user_profile(user_profile=self.user_profile)  # type: ignore
            return JsonResponse(
                {"message": f"LLMHostCompute with id {compute_id} deleted successfully."}, status=HTTPStatus.OK
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error deleting LLMHostCompute with id %s: %s",
                self.formatted_class_name,
                compute_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while deleting the LLMHostCompute: {str(e)}"},
                status=HTTPStatus.BAD_REQUEST,
            )


class LLMHostComputeListApiRenameView(SmarterAuthenticatedNeverCachedWebView):
    """
    Rename an LLMHostCompute that the authenticated user owns.

    Refused while its node group exists,
    or LLMHosts use it.
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{LLMHostComputeListApiRenameView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to rename an LLMHostCompute.

        :param kwargs: llmhost_compute_id (str): the LLMHostCompute to rename. new_name (str): its new name.
        :returns: The renamed LLMHostCompute, serialized, or an error message.
        :rtype: JsonResponse
        """
        compute_id = kwargs.get("llmhost_compute_id")
        new_name = kwargs.get("new_name")
        if not compute_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters. llmhost_compute_id: %s, new_name: %s",
                self.formatted_class_name,
                compute_id,
                new_name,
            )
            return JsonResponse(
                {"error": "llmhost_compute_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST
            )

        try:
            compute = LLMHostCompute.objects.with_ownership_permission_for(self.user_profile.user).get(id=compute_id)  # type: ignore
        except LLMHostCompute.DoesNotExist:
            logger.warning("%s.post() LLMHostCompute with id %s not found.", self.formatted_class_name, compute_id)
            return JsonResponse(
                {"error": f"LLMHostCompute with id {compute_id} not found."}, status=HTTPStatus.NOT_FOUND
            )

        try:
            compute.rename(new_name=self.to_snake_case(new_name.strip()))
            invalidate_all_cached_llmhost_computes_for_user_profile(user_profile=self.user_profile)  # type: ignore
            return JsonResponse(LLMHostComputeSerializer(compute, context={"request": request}).data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error renaming LLMHostCompute with id %s: %s",
                self.formatted_class_name,
                compute_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while renaming the LLMHostCompute: {str(e)}"},
                status=HTTPStatus.BAD_REQUEST,
            )
