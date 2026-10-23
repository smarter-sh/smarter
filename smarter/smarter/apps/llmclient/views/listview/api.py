# pylint: disable=W0613
"""
This module contains views to implement the React.

Custom Domain list view in the Smarter Dashboard.

A custom domain is owned, and shared, like every other Smarter resource: the
"owned" tab lists the user's own custom domains, and the "shared" tab those
that are shared with the user.

An llmclient that uses a custom domain depends on it (and LLMClient.custom_domain
cascades deletes), so a custom domain that an llmclient uses cannot be deleted.
Deleting a custom domain deletes the Smarter resource, not its AWS Route53 hosted zone.
"""

from http import HTTPStatus

from django.http import HttpRequest, JsonResponse

from smarter.apps.llmclient.const import CUSTOM_DOMAIN_LISTVIEW_CACHE_KIND
from smarter.apps.llmclient.models import LLMClientCustomDomain
from smarter.apps.llmclient.serializers import LLMClientCustomDomainListSerializer
from smarter.lib import logging
from smarter.lib.django.listview import SmarterListApiView
from smarter.lib.django.pagination import DEFAULT_SORT_FIELDS
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])

SORT_FIELDS = {
    **DEFAULT_SORT_FIELDS,
    "domainName": "domain_name",
    "llmclient": "llmclient__name",
    "awsHostedZoneId": "aws_hosted_zone_id",
    "verificationStatus": "verification_status",
}
"""The columns of the Custom Domain list that it may be sorted by, and the fields that sort them."""


class CustomDomainListApiView(SmarterListApiView):
    """
    Return the custom domains available to the authenticated user, for the.

    @smarter/custom-domain-list React app.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments, including ``ownership_filter``: owned, shared or all.
    :type kwargs: dict

    :returns: The user, the Smarter admin, and a page of custom domains, as JSON.
    :rtype: JsonResponse
    """

    model = LLMClientCustomDomain
    serializer_class = LLMClientCustomDomainListSerializer
    listview_cache_kind = CUSTOM_DOMAIN_LISTVIEW_CACHE_KIND
    sort_fields = SORT_FIELDS
    select_related = ("llmclient__user_profile__user",)


class CustomDomainListApiCloneView(SmarterAuthenticatedNeverCachedWebView):
    """Clone a custom domain for the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{CustomDomainListApiCloneView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Clone a custom domain that the user may read, to a new custom domain owned by the user.

        :param kwargs: ``custom_domain_id``, the id of the custom domain to clone, and ``new_name``, the clone's name.
        :returns: The clone, or an error message.
        :rtype: JsonResponse
        """
        custom_domain_id = kwargs.get("custom_domain_id")
        new_name = kwargs.get("new_name")
        if not custom_domain_id or not new_name:
            return JsonResponse({"error": "custom_domain_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)
        try:
            custom_domain = LLMClientCustomDomain.objects.with_read_permission_for(self.user_profile.user).get(id=custom_domain_id)  # type: ignore
        except LLMClientCustomDomain.DoesNotExist:
            logger.warning(
                "%s.post() Custom domain with id %s not found for cloning.", self.formatted_class_name, custom_domain_id
            )
            return JsonResponse(
                {"error": f"Custom domain with id {custom_domain_id} not found."}, status=HTTPStatus.NOT_FOUND
            )
        try:
            new_name = self.to_snake_case(new_name.strip())
            cloned = custom_domain.clone(new_name=new_name, user_profile=self.user_profile)  # type: ignore
            data = LLMClientCustomDomainListSerializer(cloned, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error cloning custom domain with id %s: %s",
                self.formatted_class_name,
                custom_domain_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while cloning the custom domain: {str(e)}"},
                status=HTTPStatus.BAD_REQUEST,
            )


class CustomDomainListApiDeleteView(SmarterAuthenticatedNeverCachedWebView):
    """Delete a custom domain owned by the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{CustomDomainListApiDeleteView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Delete a custom domain that the user owns, and that no llmclient uses.

        :param kwargs: ``custom_domain_id``, the id of the custom domain to delete.
        :returns: A confirmation, or an error message.
        :rtype: JsonResponse
        """
        custom_domain_id = kwargs.get("custom_domain_id")
        if not custom_domain_id:
            return JsonResponse({"error": "custom_domain_id is required."}, status=HTTPStatus.BAD_REQUEST)
        try:
            custom_domain = LLMClientCustomDomain.objects.with_ownership_permission_for(self.user_profile.user).get(id=custom_domain_id)  # type: ignore
        except LLMClientCustomDomain.DoesNotExist:
            logger.warning(
                "%s.post() Custom domain with id %s not found for deletion.",
                self.formatted_class_name,
                custom_domain_id,
            )
            return JsonResponse(
                {"error": f"Custom domain with id {custom_domain_id} not found."}, status=HTTPStatus.NOT_FOUND
            )
        llmclient = getattr(custom_domain, "llmclient", None)
        if llmclient is not None:
            return JsonResponse(
                {
                    "error": f"Custom domain {custom_domain.name} cannot be deleted, because LLMClient {llmclient.name} uses it."
                },
                status=HTTPStatus.BAD_REQUEST,
            )
        try:
            custom_domain.delete()
            return JsonResponse(
                {"message": f"Custom domain with id {custom_domain_id} deleted successfully."}, status=HTTPStatus.OK
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error deleting custom domain with id %s: %s",
                self.formatted_class_name,
                custom_domain_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while deleting the custom domain: {str(e)}"},
                status=HTTPStatus.BAD_REQUEST,
            )


class CustomDomainListApiRenameView(SmarterAuthenticatedNeverCachedWebView):
    """Rename a custom domain owned by the authenticated user."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{CustomDomainListApiRenameView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Rename a custom domain that the user owns.

        This renames the Smarter resource, not its domain name.

        :param kwargs: ``custom_domain_id``, the id of the custom domain to rename, and ``new_name``, its new name.
        :returns: The renamed custom domain, or an error message.
        :rtype: JsonResponse
        """
        custom_domain_id = kwargs.get("custom_domain_id")
        new_name = kwargs.get("new_name")
        if not custom_domain_id or not new_name:
            return JsonResponse({"error": "custom_domain_id and new_name are required."}, status=HTTPStatus.BAD_REQUEST)
        try:
            custom_domain = LLMClientCustomDomain.objects.with_ownership_permission_for(self.user_profile.user).get(id=custom_domain_id)  # type: ignore
        except LLMClientCustomDomain.DoesNotExist:
            logger.warning(
                "%s.post() Custom domain with id %s not found for renaming.",
                self.formatted_class_name,
                custom_domain_id,
            )
            return JsonResponse(
                {"error": f"Custom domain with id {custom_domain_id} not found."}, status=HTTPStatus.NOT_FOUND
            )
        try:
            new_name = self.to_snake_case(new_name.strip())
            custom_domain.rename(new_name=new_name)
            data = LLMClientCustomDomainListSerializer(custom_domain, context={"request": request}).data
            return JsonResponse(data, status=HTTPStatus.OK)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.post() Error renaming custom domain with id %s: %s",
                self.formatted_class_name,
                custom_domain_id,
                str(e),
                exc_info=True,
            )
            return JsonResponse(
                {"error": f"An error occurred while renaming the custom domain: {str(e)}"},
                status=HTTPStatus.BAD_REQUEST,
            )
