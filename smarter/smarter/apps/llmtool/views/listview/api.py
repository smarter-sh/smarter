# pylint: disable=W0613
"""
This module contains views to implement the React.

Plugin list view in the Smarter Dashboard.
"""

from http import HTTPStatus
from typing import Union

from django.core.handlers.asgi import ASGIRequest
from django.db import models
from django.http import HttpRequest, JsonResponse

from smarter.apps.account.serializers import UserProfileSerializer
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmtool.caching import (
    get_cached_plugins_available_to_user_profile,
    get_cached_plugins_owned_by_user_profile,
    get_cached_plugins_shared_with_user_profile,
    invalidate_all_cached_plugins_for_user_profile,
)
from smarter.apps.llmtool.manifest.controller import PluginController
from smarter.apps.llmtool.models import Extension, PluginMeta
from smarter.apps.llmtool.plugin.base import SmarterPluginError
from smarter.apps.llmtool.serializers import PluginSerializer
from smarter.common.enum import SmarterResourceOwnershipFilterEnum
from smarter.lib import logging
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
)
from smarter.lib.django.pagination import (
    DEFAULT_SORT_FIELDS,
    ListViewPagination,
    paginate_listview,
)
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .contract import ExtensionListItem, ExtensionListPage

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])

SORT_FIELDS = {
    **DEFAULT_SORT_FIELDS,
    "kind": "plugin_class",
    "selector": "plugin_selector_plugin__directive",
}
"""The columns of the Plugin list that it may be sorted by, and the fields that sort them."""

EXTENSION_SORT_FIELDS = {
    "displayName": "display_name",
    "description": "description",
    "publisher": "publisher",
    "version": "installed_version__version",
    "trustBadge": "trust_badge",
    "enabled": "enabled",
    "createdAt": "created_at",
    "updatedAt": "updated_at",
}
"""The columns of the Extension list that it may be sorted by, and the fields that sort them."""

EXTENSION_SEARCH_FIELDS = ("slug", "display_name", "description", "publisher")
"""The fields of an Extension that a search of the Extension list matches."""


class PluginListApiView(SmarterAuthenticatedNeverCachedWebView):
    """
    Render the plugin list view for the Smarter Workbench web console.

    This view displays all plugins available to the authenticated user as cards, providing a quick overview and access to plugin details.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    :returns: Rendered HTML page with a card for each plugin, or a 404 error page if the user is not authenticated.
    :rtype: HttpResponse
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{PluginListApiView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def get(self, request: ASGIRequest, *args, **kwargs) -> Union[JsonResponse, SmarterHttpResponseNotFound]:
        """Return the same json as a POST, so that the list api can be browsed."""
        return self.post(request, *args, **kwargs)

    def post(self, request: ASGIRequest, *args, **kwargs) -> Union[JsonResponse, SmarterHttpResponseNotFound]:
        qs: models.QuerySet[PluginMeta]
        ownership_filter = kwargs.get("ownership_filter", SmarterResourceOwnershipFilterEnum.ALL)
        invalidate_cache = request.GET.get("invalidate_cache", "false").lower() == "true"

        logger.debug(
            "%s.get() Rendering plugin list view for user %s with args=%s, kwargs=%s.",
            self.formatted_class_name,
            request.user.username if request.user else "None",  # type: ignore[union-attr]
            args,
            kwargs,
        )
        if invalidate_cache:
            invalidate_all_cached_plugins_for_user_profile(user_profile=self.user_profile)  # type: ignore

        if ownership_filter == SmarterResourceOwnershipFilterEnum.OWNED:
            qs = get_cached_plugins_owned_by_user_profile(user_profile=self.user_profile)  # type: ignore

        elif ownership_filter == SmarterResourceOwnershipFilterEnum.SHARED:
            qs = get_cached_plugins_shared_with_user_profile(user_profile=self.user_profile)  # type: ignore

        elif ownership_filter == SmarterResourceOwnershipFilterEnum.ALL:
            qs = get_cached_plugins_available_to_user_profile(user_profile=self.user_profile)  # type: ignore
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

        plugins, pagination = paginate_listview(request, qs.order_by("-updated_at"), sort_fields=SORT_FIELDS)

        smarter_admin = smarter_cached_objects.smarter_admin_user_profile
        retval = {
            "user": UserProfileSerializer(self.user_profile).data,
            "admin": UserProfileSerializer(smarter_admin).data,
            "objects": PluginSerializer(plugins, many=True, context={"request": request}).data,
            "pagination": pagination,
        }
        return JsonResponse(retval)


class PluginListApiExtensionsView(SmarterAuthenticatedNeverCachedWebView):
    """
    List the installed Extensions that the authenticated user's account may use, read-only.

    This is the api of the LLMTool list's Extensions tab. An extension is listed if it has an
    installed version and is available to the user's account, whether or not it is enabled:
    an LLMClient may list a disabled extension, whose tools are offered once an administrator
    enables it (see the LLMClient broker's ``resolve_extension()``). A superuser sees every
    installed extension.

    It has no clone, rename or delete: superusers manage extensions in the Extensions console.
    The response is paginated, searched and sorted like the plugin list's, with
    :func:`~smarter.lib.django.pagination.paginate_listview`, and is an
    :class:`~smarter.apps.llmtool.views.listview.contract.ExtensionListPage`, whose JSON Schema
    ``@smarter/llmtool-list`` generates its types from.
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{PluginListApiExtensionsView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def available_extensions(self, request: ASGIRequest) -> models.QuerySet[Extension]:
        """
        Return the installed extensions that the user's account may use.

        This is the queryset form of :meth:`~smarter.apps.llmtool.models.Extension.is_available_to`.

        :param request: The HTTP request, of an authenticated user.
        :returns: The extensions, every installed one for a superuser.
        """
        qs = Extension.objects.filter(installed_version__isnull=False).select_related("installed_version")
        qs = qs.defer("installed_version__archive")
        if request.user.is_superuser:  # type: ignore[union-attr]
            return qs
        account = self.user_profile.account  # type: ignore[union-attr]
        return qs.filter(models.Q(all_accounts=True) | models.Q(accounts=account)).distinct()

    def post(self, request: ASGIRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests for a page of the extensions that the user may use.

        :param request: The HTTP request, whose query parameters are ``page``, ``page_size``,
            ``search`` and ``ordering``. See :func:`~smarter.lib.django.pagination.paginate_listview`.
        :returns: An :class:`~smarter.apps.llmtool.views.listview.contract.ExtensionListPage`:
            ``{"objects": [...], "pagination": {...}}``.
        :rtype: JsonResponse
        """
        logger.debug(
            "%s.post() Listing the extensions available to user %s.",
            self.formatted_class_name,
            request.user.username if request.user else "None",  # type: ignore[union-attr]
        )
        extensions, pagination = paginate_listview(
            request,
            self.available_extensions(request).order_by("display_name"),
            search_fields=EXTENSION_SEARCH_FIELDS,
            sort_fields=EXTENSION_SORT_FIELDS,
        )
        page = ExtensionListPage(
            objects=[ExtensionListItem.from_model(extension) for extension in extensions],
            pagination=ListViewPagination.model_validate(pagination),
        )
        return JsonResponse(page.to_json())


class PluginListApiCloneView(SmarterAuthenticatedNeverCachedWebView):
    """Clone a plugin for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{PluginListApiCloneView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to clone an existing PluginMeta.

        Validates input
        parameters, checks for the existence of the PluginMeta to be cloned, and
        creates a new PluginMeta with the specified name. Invalidates the cache
        for the user's LLMClients after cloning.

        :param request: The HTTP request object containing the parameters for cloning.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - llmclient_id (str): The ID of the PluginMeta to be cloned.
            - new_name (str): The new name for the cloned PluginMeta.

        :returns: A JsonResponse containing the serialized data of the newly cloned PluginMeta if successful, or an error message if the cloning fails.
        :rtype: JsonResponse
        """
        llmclient_id = kwargs.get("llmclient_id")
        new_name = kwargs.get("new_name")
        llmclient: PluginMeta

        if not llmclient_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters. llmclient_id: %s, new_name: %s",
                self.formatted_class_name,
                llmclient_id,
                new_name,
            )
            return JsonResponse({"error": "llmclient_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            llmclient = PluginMeta.objects.with_read_permission_for(self.user_profile.user).get(id=llmclient_id)  # type: ignore
        except PluginMeta.DoesNotExist:
            logger.warning(
                "%s.post() PluginMeta with id %s not found for cloning.", self.formatted_class_name, llmclient_id
            )
            return JsonResponse({"error": f"PluginMeta with id {llmclient_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            # PluginMeta.clone() copies only the PluginMeta, whereas the plugin's
            # clone() also copies its selector, prompt and data.
            plugin = PluginController(user_profile=self.user_profile, plugin_meta=llmclient).plugin  # type: ignore[arg-type]
            if not plugin or not plugin.ready:
                raise SmarterPluginError(f"PluginMeta with id {llmclient_id} is not ready, and cannot be cloned.")
            cloned_id = plugin.clone(new_name=new_name, user_profile=self.user_profile)
            if not cloned_id:
                raise SmarterPluginError(f"PluginMeta with id {llmclient_id} could not be cloned.")
            cloned_llmclient = PluginMeta.objects.get(id=cloned_id)
            invalidate_all_cached_plugins_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = PluginSerializer(cloned_llmclient, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error cloning PluginMeta with id %s: %s",
                self.formatted_class_name,
                llmclient_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while cloning the PluginMeta: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class PluginListApiDeleteView(SmarterAuthenticatedNeverCachedWebView):
    """Delete a plugin for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{PluginListApiDeleteView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to delete an existing PluginMeta.

        Validates input
        parameters, checks for the existence of the PluginMeta to be deleted, and
        deletes the PluginMeta if it exists. Invalidates the cache for the user's
        LLMClients after deletion.

        :param request: The HTTP request object containing the parameters for deletion.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - llmclient_id (str): The ID of the PluginMeta to be deleted.

        :returns: A JsonResponse indicating the success or failure of the deletion.
        :rtype: JsonResponse
        """
        llmclient_id = kwargs.get("llmclient_id")
        if not llmclient_id:
            logger.warning("%s.post() Missing required parameter llmclient_id for deletion.", self.formatted_class_name)
            return JsonResponse({"error": "llmclient_id is required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            llmclient = PluginMeta.objects.with_ownership_permission_for(self.user_profile.user).get(id=llmclient_id)  # type: ignore
        except PluginMeta.DoesNotExist:
            logger.warning(
                "%s.post() PluginMeta with id %s not found for deletion.", self.formatted_class_name, llmclient_id
            )
            return JsonResponse({"error": f"PluginMeta with id {llmclient_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            llmclient.delete()
            invalidate_all_cached_plugins_for_user_profile(user_profile=self.user_profile)  # type: ignore
            return JsonResponse(
                {"message": f"PluginMeta with id {llmclient_id} deleted successfully."}, status=HTTPStatus.OK
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error deleting PluginMeta with id %s: %s",
                self.formatted_class_name,
                llmclient_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while deleting the PluginMeta: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class PluginListApiRenameView(SmarterAuthenticatedNeverCachedWebView):
    """Rename a plugin for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{PluginListApiRenameView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to rename an existing PluginMeta.

        Validates input
        parameters, checks for the existence of the PluginMeta to be renamed, and
        renames the PluginMeta if it exists. Invalidates the cache for the user's
        LLMClients after renaming.

        :param request: The HTTP request object containing the parameters for renaming.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - llmclient_id (str): The ID of the PluginMeta to be renamed.
            - new_name (str): The new name for the PluginMeta.

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
            llmclient = PluginMeta.objects.with_ownership_permission_for(self.user_profile.user).get(id=llmclient_id)  # type: ignore
        except PluginMeta.DoesNotExist:
            logger.warning(
                "%s.post() PluginMeta with id %s not found for renaming.", self.formatted_class_name, llmclient_id
            )
            return JsonResponse({"error": f"PluginMeta with id {llmclient_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            llmclient.rename(new_name=new_name)
            invalidate_all_cached_plugins_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = PluginSerializer(llmclient, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error renaming PluginMeta with id %s: %s",
                self.formatted_class_name,
                llmclient_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while renaming the PluginMeta: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )
