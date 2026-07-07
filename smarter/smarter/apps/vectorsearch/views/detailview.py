# pylint: disable=W0613
"""
This module contains views to implement the Vectorsearch.

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
from smarter.apps.vectorsearch.models import Vectorsearch
from smarter.common.helpers.console_helpers import formatted_json
from smarter.lib import logging
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
    SmarterHttpResponseServerError,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROVIDER_LOGGING])


class VectorsearchDetailView(DocsBaseView):
    """
    Renders the detail view for a Smarter dashboard vectorsearch.

    This view renders a detailed manifest for a specific vectorsearch, including its configuration and metadata, in YAML format. It is intended for authenticated users and provides error handling for missing or unsupported vectorsearch kinds and names.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Keyword arguments, must include 'name' (vectorsearch name) and 'kind' (vectorsearch type).
    :type kwargs: dict

    :returns: Rendered HTML page with vectorsearch manifest details, or a 404 error page if the vectorsearch is not found or parameters are invalid.
    :rtype: HttpResponse

    .. note::

        The vectorsearch name and kind must be provided and valid. Otherwise, a "not found" response is returned.

    .. seealso::

        :class:`Vectorsearch` for vectorsearch metadata retrieval.
        :class:`ApiV1CliDescribeApiView` for API details.

    **Example usage**::

        GET /vectorsearch/detail/?name=my_vectorsearch&kind=custom
    """

    template_path = "common/manifest_detail.html"
    vectorsearch: Optional[Vectorsearch] = None

    def get(self, request, *args, **kwargs) -> HttpResponse:
        """
        Handle GET requests to render the vectorsearch manifest detail view.

        This method processes the incoming request to retrieve the
        specified vectorsearch's manifest details and renders them in a
        user-friendly format. It performs validation on the provided vectorsearch
        name and kind, retrieves the vectorsearch metadata, and handles any
        errors that may arise during this process.

        Process:
        1. Extract and validate 'name' and 'kind' from kwargs.
        2. Retrieve the vectorsearch metadata using the provided name and user context.
        3. If the vectorsearch is found, call the API view to get the vectorsearch details
        4. Convert the JSON response to YAML format for better readability.
        5. Render the vectorsearch manifest detail template with the retrieved data.
        6. Handle any errors that occur during the process and return appropriate error responses.

        :param request: Django HTTP request object.
        :type request: ASGIRequest
        :param args: Additional positional arguments.
        :type args: tuple
        :param kwargs: Keyword arguments, must include 'name' (vectorsearch name) and 'kind' (vectorsearch type).
        :type kwargs: dict

        :returns: Rendered HTML page with vectorsearch manifest details, or an error response if the vectorsearch is not found or parameters are invalid.
        :rtype: HttpResponse
        """

        # to avoid potential circular import issues.
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews

        hashed_id = kwargs.pop("hashed_id")
        pk_id = Vectorsearch.id_from_hashed_id(hashed_id)
        if not pk_id:
            logger.error(
                "%s.get() Invalid hashed_id provided: %s. Unable to convert to vectorsearch ID.",
                self.formatted_class_name,
                hashed_id,
            )
            return SmarterHttpResponseNotFound(request=request, error_message="Vectorsearch not found")
        try:
            self.vectorsearch = Vectorsearch.objects.get(id=pk_id, user_profile=self.user_profile)
            logger.debug(
                "%s.get() Found vectorsearch with id %s for user %s.",
                self.formatted_class_name,
                pk_id,
                self.user_profile.user.username if self.user_profile else "unknown user",
            )
        except Vectorsearch.DoesNotExist:
            try:
                if self.user_profile:

                    admin_user = UserProfile.admin_for_account(self.user_profile.account)
                    admin_user_profile = UserProfile.get_cached_object(user=admin_user)  # type: ignore
                    self.vectorsearch = Vectorsearch.objects.get(id=pk_id, user_profile=admin_user_profile)
                    logger.debug(
                        "%s.get() Found vectorsearch with id %s for admin user %s.",
                        self.formatted_class_name,
                        pk_id,
                        admin_user if admin_user else "unknown admin user",
                    )
            except Vectorsearch.DoesNotExist:
                try:
                    self.vectorsearch = Vectorsearch.objects.get(
                        id=pk_id, user_profile=smarter_cached_objects.smarter_admin_user_profile
                    )
                    logger.debug(
                        "%s.get() Found vectorsearch with id %s for smarter admin user.",
                        self.formatted_class_name,
                        pk_id,
                    )
                except Vectorsearch.DoesNotExist:
                    pass
        if not self.vectorsearch:
            logger.error(
                "%s.get() Vectorsearch with id %s not found for user %s or admin users.",
                self.formatted_class_name,
                pk_id,
                self.user_profile.user.username if self.user_profile else "unknown user",
            )
            return SmarterHttpResponseNotFound(request=request, error_message="Vectorsearch not found")

        self.kind = SAMKinds.PROVIDER

        logger.debug(
            "%s.post() Rendering vectorsearch detail view for %s, kwargs=%s.",
            self.formatted_class_name,
            self.vectorsearch.name if self.vectorsearch else "unknown vectorsearch",
            kwargs,
        )
        kwargs.pop("name", None)
        kwargs["name"] = self.vectorsearch.name if self.vectorsearch else "unknown vectorsearch"
        kwargs["kind"] = self.kind.value
        reverse_name = ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.describe
        logger.debug(
            "%s.post() calling get_brokered_json_response() with reverse_name %s, kwargs: %s",
            self.formatted_class_name,
            reverse_name,
            kwargs,
        )
        view = ApiV1CliDescribeApiView.as_view()
        json_response = self.get_brokered_json_response(
            reverse_name=reverse_name,
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
            "page_title": self.vectorsearch.name if self.vectorsearch else "unknown vectorsearch",
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
