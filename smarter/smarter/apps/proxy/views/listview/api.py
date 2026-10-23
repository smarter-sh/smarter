# pylint: disable=W0613
"""This module contains views to implement the React Proxy list view in the Smarter Dashboard."""

from http import HTTPStatus

from django.http import HttpRequest, JsonResponse

from smarter.apps.proxy.caching import (
    invalidate_all_cached_proxies_for_user_profile,
)
from smarter.apps.proxy.models import Proxy
from smarter.apps.proxy.serializers import ProxySerializer
from smarter.lib import logging
from smarter.lib.django.listview import SmarterListApiView
from smarter.lib.django.pagination import DEFAULT_SORT_FIELDS
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROXY_LOGGING])

SORT_FIELDS = {
    **DEFAULT_SORT_FIELDS,
    "providerName": "provider__name",
}
"""The columns of the Proxy list that it may be sorted by, and the fields that sort them."""


class ProxyListApiView(SmarterListApiView):
    """
    The JSON API of the web console's Proxy list view.

    Returns a page of the Proxies that the user owns, that are shared with them, or both,
    according to ``ownership_filter``: ``owned``, ``shared`` or ``all``.

    Query parameters: ``page``, ``page_size``, ``search``, ``ordering`` (a column of
    :data:`SORT_FIELDS`) and ``invalidate_cache``.

    :returns: ``{"user": ..., "admin": ..., "objects": [...], "pagination": {...}}``, where objects are
        serialized by :class:`~smarter.apps.proxy.serializers.ProxySerializer`, and pagination is
        described by :func:`~smarter.lib.django.pagination.paginate_listview`.
    :rtype: JsonResponse
    """

    model = Proxy
    serializer_class = ProxySerializer
    listview_cache_kind = "Proxy"
    sort_fields = SORT_FIELDS


class ProxyListApiCloneView(SmarterAuthenticatedNeverCachedWebView):
    """Clone a proxy for the authenticated user."""

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to clone an existing Proxy.

        Validates input
        parameters, checks for the existence of the Proxy to be cloned, and
        creates a new Proxy with the specified name. Invalidates the cache
        for the user's Proxies after cloning.

        :param request: The HTTP request object containing the parameters for cloning.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - proxy_id (str): The ID of the Proxy to be cloned.
            - new_name (str): The new name for the cloned Proxy.

        :returns: A JsonResponse containing the serialized data of the newly cloned Proxy if successful, or an error message if the cloning fails.
        :rtype: JsonResponse
        """
        proxy_id = kwargs.get("proxy_id")
        new_name = kwargs.get("new_name")
        proxy: Proxy

        if not proxy_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters. proxy_id: %s, new_name: %s",
                self.formatted_class_name,
                proxy_id,
                new_name,
            )
            return JsonResponse({"error": "proxy_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            proxy = Proxy.objects.with_read_permission_for(self.user_profile.user).get(id=proxy_id)  # type: ignore
        except Proxy.DoesNotExist:
            logger.warning("%s.post() Proxy with id %s not found for cloning.", self.formatted_class_name, proxy_id)
            return JsonResponse({"error": f"Proxy with id {proxy_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            cloned_proxy = proxy.clone(new_name=new_name, user_profile=self.user_profile)  # type: ignore
            invalidate_all_cached_proxies_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = ProxySerializer(cloned_proxy, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error cloning Proxy with id %s: %s",
                self.formatted_class_name,
                proxy_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while cloning the Proxy: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class ProxyListApiDeleteView(SmarterAuthenticatedNeverCachedWebView):
    """Delete a proxy for the authenticated user."""

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to delete an existing Proxy.

        Validates input
        parameters, checks for the existence of the Proxy to be deleted, and
        deletes the Proxy if it exists. Invalidates the cache for the user's
        LLMClients after deletion.

        :param request: The HTTP request object containing the parameters for deletion.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - proxy_id (str): The ID of the Proxy to be deleted.

        :returns: A JsonResponse indicating the success or failure of the deletion.
        :rtype: JsonResponse
        """
        proxy_id = kwargs.get("proxy_id")
        if not proxy_id:
            logger.warning("%s.post() Missing required parameter proxy_id for deletion.", self.formatted_class_name)
            return JsonResponse({"error": "proxy_id is required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            proxy = Proxy.objects.with_ownership_permission_for(self.user_profile.user).get(id=proxy_id)  # type: ignore
        except Proxy.DoesNotExist:
            logger.warning("%s.post() Proxy with id %s not found for deletion.", self.formatted_class_name, proxy_id)
            return JsonResponse({"error": f"Proxy with id {proxy_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            proxy.delete()
            invalidate_all_cached_proxies_for_user_profile(user_profile=self.user_profile)  # type: ignore
            return JsonResponse({"message": f"Proxy with id {proxy_id} deleted successfully."}, status=HTTPStatus.OK)
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error deleting Proxy with id %s: %s",
                self.formatted_class_name,
                proxy_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while deleting the Proxy: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )


class ProxyListApiRenameView(SmarterAuthenticatedNeverCachedWebView):
    """Rename a proxy for the authenticated user."""

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Handle POST requests to rename an existing Proxy.

        Validates input
        parameters, checks for the existence of the Proxy to be renamed, and
        renames the Proxy if it exists. Invalidates the cache for the user's
        LLMClients after renaming.

        :param request: The HTTP request object containing the parameters for renaming.
        :type request: HttpRequest
        :param args: Additional positional arguments (not used).
        :param kwargs: Additional keyword arguments, including:

            - proxy_id (str): The ID of the Proxy to be renamed.
            - new_name (str): The new name for the Proxy.

        :returns: A JsonResponse indicating the success or failure of the renaming.
        :rtype: JsonResponse
        """
        proxy_id = kwargs.get("proxy_id")
        new_name = kwargs.get("new_name")
        if not proxy_id or not new_name:
            logger.warning(
                "%s.post() Missing required parameters for renaming. proxy_id: %s, new_name: %s",
                self.formatted_class_name,
                proxy_id,
                new_name,
            )
            return JsonResponse({"error": "proxy_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)

        try:
            proxy = Proxy.objects.with_ownership_permission_for(self.user_profile.user).get(id=proxy_id)  # type: ignore
        except Proxy.DoesNotExist:
            logger.warning("%s.post() Proxy with id %s not found for renaming.", self.formatted_class_name, proxy_id)
            return JsonResponse({"error": f"Proxy with id {proxy_id} not found."}, status=HTTPStatus.NOT_FOUND)

        try:
            new_name = self.to_snake_case(new_name.strip())
            proxy.rename(new_name=new_name)
            invalidate_all_cached_proxies_for_user_profile(user_profile=self.user_profile)  # type: ignore
            data = ProxySerializer(proxy, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error renaming Proxy with id %s: %s",
                self.formatted_class_name,
                proxy_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while renaming the Proxy: {str(e)}"}, status=HTTPStatus.BAD_REQUEST
            )
