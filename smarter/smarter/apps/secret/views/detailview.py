# pylint: disable=W0613
"""
This module contains views to implement the Secret
card-style detail view in the Smarter Dashboard.
"""

from typing import Optional

import yaml
from django.http import HttpResponse
from django.shortcuts import render

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.api.v1.cli.views.describe import ApiV1CliDescribeApiView
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.docs.views.base import DocsBaseView
from smarter.apps.secret.models import Secret
from smarter.common.helpers.console_helpers import formatted_json
from smarter.lib import logging
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
    SmarterHttpResponseServerError,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.SECRET_LOGGING])


class SecretDetailView(DocsBaseView):
    """
    Renders the detail view for a Smarter dashboard secret.

    This view renders a detailed manifest for a specific secret, including its configuration and metadata, in YAML format. It is intended for authenticated users and provides error handling for missing or unsupported secret kinds and names.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Keyword arguments, must include 'name' (secret name) and 'kind' (secret type).
    :type kwargs: dict

    :returns: Rendered HTML page with secret manifest details, or a 404 error page if the secret is not found or parameters are invalid.
    :rtype: HttpResponse

    .. note::

        The secret name and kind must be provided and valid. Otherwise, a "not found" response is returned.

    .. seealso::

        :class:`Secret` for secret metadata retrieval.
        :class:`ApiV1CliDescribeApiView` for API details.

    **Example usage**::

        GET /secret/detail/?name=my_secret&kind=custom

    """

    template_path = "common/manifest_detail.html"
    secret: Optional[Secret] = None

    def get(self, request, *args, **kwargs) -> HttpResponse:
        """
        Handle GET requests to render the secret manifest detail view.
        This method processes the incoming request to retrieve the
        specified secret's manifest details and renders them in a
        user-friendly format. It performs validation on the provided secret
        name and kind, retrieves the secret metadata, and handles any
        errors that may arise during this process.

        Process:
        1. Extract and validate 'name' and 'kind' from kwargs.
        2. Retrieve the secret metadata using the provided name and user context.
        3. If the secret is found, call the API view to get the secret details
        4. Convert the JSON response to YAML format for better readability.
        5. Render the secret manifest detail template with the retrieved data.
        6. Handle any errors that occur during the process and return appropriate error responses.

        :param request: Django HTTP request object.
        :type request: ASGIRequest
        :param args: Additional positional arguments.
        :type args: tuple
        :param kwargs: Keyword arguments, must include 'name' (secret name) and 'kind' (secret type).
        :type kwargs: dict

        :returns: Rendered HTML page with secret manifest details, or an error response if the secret is not found or parameters are invalid.
        :rtype: HttpResponse
        """

        # to avoid potential circular import issues.
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews

        secret_id = kwargs.pop("secret_id")
        try:
            self.secret = Secret.objects.get(id=secret_id, user_profile=self.user_profile)
        except Secret.DoesNotExist:
            try:
                if self.user_profile:

                    admin_user = UserProfile.admin_for_account(self.user_profile.account)
                    admin_user_profile = UserProfile.get_cached_object(user=admin_user)  # type: ignore
                    self.secret = Secret.objects.get(id=secret_id, user_profile=admin_user_profile)
            except Secret.DoesNotExist:
                try:
                    self.secret = Secret.objects.get(
                        id=secret_id, user_profile=smarter_cached_objects.smarter_admin_user_profile
                    )
                except Secret.DoesNotExist:
                    pass
        self.kind = SAMKinds.SECRET

        logger.debug(
            "%s.post() Rendering secret detail view for %s, kwargs=%s.",
            self.formatted_class_name,
            self.secret.name if self.secret else "unknown secret",
            kwargs,
        )
        kwargs.pop("name", None)
        kwargs["name"] = self.secret.name if self.secret else "unknown secret"
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
                "%s.dispatch() - Error converting JSON response to YAML: %s. JSON response: %s",
                self.formatted_class_name,
                str(e),
                formatted_json(json_response),
            )
            return SmarterHttpResponseServerError(request=request, error_message="Error converting manifest to YAML")

        context = {
            "manifest": yaml_response,
            "page_title": self.secret.name if self.secret else "unknown secret",
        }

        if not self.template_path:
            logger.error("%s.post() self.template_path is not set.", self.formatted_class_name)
            return SmarterHttpResponseNotFound(request=request, error_message="Template path not set")

        try:
            response = render(request, self.template_path, context=context)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.dispatch() - Error rendering template: %s. context: %s",
                self.formatted_class_name,
                str(e),
                formatted_json(context),
            )
            return SmarterHttpResponseServerError(request=request, error_message="Error rendering manifest page")
        return response
