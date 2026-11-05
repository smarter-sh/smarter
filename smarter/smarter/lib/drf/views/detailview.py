# pylint: disable=W0613
"""The web console's detail view of an API key (AuthToken), which shows its manifest as YAML."""

from typing import Optional

import yaml
from django.http import HttpResponse
from django.shortcuts import render

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.api.v1.cli.views.describe import ApiV1CliDescribeApiView
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.docs.views.base import DocsBaseView
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.lib import logging
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
    SmarterHttpResponseServerError,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.models import SmarterAuthToken as AuthToken

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.SECRET_LOGGING])


class AuthTokenDetailView(DocsBaseView):
    """
    Renders the web console's detail page of an API key.

    This view renders the manifest of an API key, including its configuration and metadata, in
    YAML format. It is intended for authenticated users. The key is identified by its ``key_id``,
    the ``authtoken_id`` url parameter.

    .. seealso::

        :class:`~smarter.lib.drf.models.SmarterAuthToken` for the API key model.
        :class:`~smarter.apps.api.v1.cli.views.describe.ApiV1CliDescribeApiView`, which builds the manifest.

    **Example usage**::

        GET /authtoken/d55cfbe5-89ec-4c11-90b9-3e9ec4bbbd85/
    """

    template_path = "common/manifest_detail.html"
    authtoken: Optional[AuthToken] = None

    def get(self, request, *args, **kwargs) -> HttpResponse:
        """
        Render the API key's manifest, as YAML.

        Process:

        1. Look up the API key by ``authtoken_id``, owned by the user's profile, then by the
           account's admin, then by the Smarter admin.
        2. Call the cli api's describe view for the key's name.
        3. Convert the JSON response to YAML format for better readability.
        4. Render the manifest detail template with the YAML.

        :param request: The Django HTTP request.
        :param args: Passed to the describe view.
        :param kwargs: The url parameters, which must include ``authtoken_id``, the key's ``key_id``.
        :returns: The rendered page, or an error response if the manifest can't be converted to
            YAML or the page can't be rendered.
        """

        # to avoid potential circular import issues.
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews

        authtoken_id = kwargs.pop("authtoken_id")
        try:
            self.authtoken = AuthToken.objects.get(key_id=authtoken_id, user_profile=self.user_profile)
        except AuthToken.DoesNotExist:
            try:
                if self.user_profile:

                    admin_user = UserProfile.admin_for_account(self.user_profile.account)
                    admin_user_profile = UserProfile.get_cached_object(user=admin_user)  # type: ignore
                    self.authtoken = AuthToken.objects.get(key_id=authtoken_id, user_profile=admin_user_profile)
            except AuthToken.DoesNotExist:
                try:
                    self.authtoken = AuthToken.objects.get(
                        key_id=authtoken_id, user_profile=smarter_cached_objects.smarter_admin_user_profile
                    )
                except AuthToken.DoesNotExist:
                    pass
        self.kind = SAMKinds.AUTH_TOKEN

        logger.debug(
            "%s.get() Rendering authtoken detail view for %s, kwargs=%s.",
            self.formatted_class_name,
            self.authtoken.name if self.authtoken else "unknown authtoken",
            kwargs,
        )
        kwargs.pop("name", None)
        kwargs["name"] = self.authtoken.name if self.authtoken else "unknown authtoken"
        kwargs["kind"] = self.kind.value
        view = ApiV1CliDescribeApiView.as_view()
        json_response = self.get_brokered_json_response(
            reverse_name=ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.describe,
            view=view,
            request=request,
            *args,
            **kwargs,
        )

        try:
            yaml_response = yaml.dump(json_response, default_flow_style=False)
        except yaml.YAMLError as e:
            logger.error(
                "%s.get() - Error converting JSON response to YAML: %s. JSON response: %s",
                self.formatted_class_name,
                str(e),
                SmarterFormattedText.json(json_response),
            )
            return SmarterHttpResponseServerError(request=request, error_message="Error converting manifest to YAML")

        context = {
            "manifest": yaml_response,
            "page_title": self.authtoken.name if self.authtoken else "unknown authtoken",
        }

        if not self.template_path:
            logger.error("%s.get() self.template_path is not set.", self.formatted_class_name)
            return SmarterHttpResponseNotFound(request=request, error_message="Template path not set")

        try:
            response = render(request, self.template_path, context=context)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.get() - Error rendering template: %s. context: %s",
                self.formatted_class_name,
                str(e),
                SmarterFormattedText.json(context),
            )
            return SmarterHttpResponseServerError(request=request, error_message="Error rendering manifest page")
        return response
