# pylint: disable=W0613
"""
smarter.apps.plugin.views.vectorstore
This module contains views to implement the card-style list view
in the Smarter Dashboard.
"""

import logging
from typing import Optional

import yaml
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import render

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.cli.views.describe import ApiV1CliDescribeApiView
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.docs.views.base import DocsBaseView
from smarter.apps.vectorstore.models import VectorDatabase
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.helpers.console_helpers import formatted_json
from smarter.common.utils.request import is_authenticated_request
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
    SmarterHttpResponseServerError,
)
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


# pylint: disable=unused-argument
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.VECTORSTORE_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class VectorstoreManifestView(DocsBaseView):
    """
    Renders the detail view for a Smarter dashboard vectorstore.

    This view renders a detailed manifest for a specific vectorstore, including its configuration and metadata, in YAML format. It is intended for authenticated users and provides error handling for missing or unsupported vectorstore kinds and names.

    :param request: Django HTTP request object.
    :type request: WSGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Keyword arguments, must include 'name' (vectorstore name) and 'kind' (vectorstore type).
    :type kwargs: dict

    :returns: Rendered HTML page with vectorstore manifest details, or a 404 error page if the vectorstore is not found or parameters are invalid.
    :rtype: HttpResponse

    .. note::

        The vectorstore name and kind must be provided and valid. Otherwise, a "not found" response is returned.

    .. seealso::

        :class:`VectorDatabase` for vectorstore metadata retrieval.
        :class:`ApiV1CliDescribeApiView` for API details.

    **Example usage**::

        GET /vectorstore/detail/?name=my_vectorstore&kind=custom

    """

    template_path = "plugin/manifest_detail.html"
    vectorstore: Optional[VectorDatabase] = None
    backend: str

    def get(self, request, *args, **kwargs) -> HttpResponse:
        """
        Handle GET requests to render the vectorstore manifest detail view.
        This method processes the incoming request to retrieve the
        specified vectorstore's manifest details and renders them in a
        user-friendly format. It performs validation on the provided vectorstore
        name and kind, retrieves the vectorstore metadata, and handles any
        errors that may arise during this process.

        Process:
        1. Extract and validate 'name' and 'kind' from kwargs.
        2. Retrieve the vectorstore metadata using the provided name and user context.
        3. If the vectorstore is found, call the API view to get the vectorstore details
        4. Convert the JSON response to YAML format for better readability.
        5. Render the vectorstore manifest detail template with the retrieved data.
        6. Handle any errors that occur during the process and return appropriate error responses.

        :param request: Django HTTP request object.
        :type request: WSGIRequest
        :param args: Additional positional arguments.
        :type args: tuple
        :param kwargs: Keyword arguments, must include 'name' (vectorstore name) and 'kind' (vectorstore type).
        :type kwargs: dict

        :returns: Rendered HTML page with vectorstore manifest details, or an error response if the vectorstore is not found or parameters are invalid.
        :rtype: HttpResponse
        """

        self.name = kwargs.pop("name", None)
        self.kind = SAMKinds.str_to_kind(kwargs.pop("kind", None))
        self.backend = kwargs.pop("backend", None)
        if self.kind is None:
            logger.error("%s.setup() Vectorstore kind is required but not provided.", self.formatted_class_name)
            return SmarterHttpResponseNotFound(request=request, error_message="Vectorstore kind is required")
        if self.kind != SAMKinds.VECTORSTORE:
            logger.error("%s.setup() Vectorstore kind %s is not supported.", self.formatted_class_name, self.kind)
            return SmarterHttpResponseNotFound(
                request=request, error_message=f"Vectorstore kind {self.kind} is not supported"
            )
        if self.backend is None:
            logger.error("%s.setup() Vectorstore backend is required but not provided.", self.formatted_class_name)
            return SmarterHttpResponseNotFound(request=request, error_message="Vectorstore backend is required")
        if not self.name:
            logger.error("%s.setup() Vectorstore name is required but not provided.", self.formatted_class_name)
            return SmarterHttpResponseNotFound(request=request, error_message="Vectorstore name is required")
        if not is_authenticated_request(request):
            logger.error("%s.setup() User is not authenticated.", self.formatted_class_name)
            return SmarterHttpResponseNotFound(request=request, error_message="User is not authenticated")
        self.vectorstore = VectorDatabase.get_cached_object(
            user=request.user, kind=self.kind, name=self.name, backend=self.backend  # type: ignore[arg-type]
        )
        if not self.vectorstore:
            logger.error("%s.post() Vectorstore %s of kind %s and backend %s not found for user %s.", self.formatted_class_name, self.name, self.kind, self.backend, request.user.username)  # type: ignore[union-attr]
            return SmarterHttpResponseNotFound(request=request, error_message="Vectorstore not found")

        logger.info(
            "%s.post() Rendering vectorstore detail view for %s of kind %s and backend %s, kwargs=%s.",
            self.formatted_class_name,
            self.name,
            self.kind,
            self.backend,
            kwargs,
        )
        # get_brokered_json_response() adds self.kind to kwargs, so we remove it here.
        # TypeError: smarter.apps.api.v1.cli.views.describe.View.as_view.<locals>.view() got multiple values for keyword argument 'kind'
        kwargs.pop("kind", None)
        kwargs["name"] = self.name
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
            "page_title": self.name,
        }
        if not self.template_path:
            raise SmarterConfigurationError("self.template_path not set.")

        try:
            response = render(request, self.template_path, context=context)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.dispatch() - Error rendering template: %s. context: %s",
                self.formatted_class_name,
                str(e),
                formatted_json(context),
                exec_info=True,
            )
            return SmarterHttpResponseServerError(request=request, error_message="Error rendering manifest page")
        return response


class VectorstoreListView(SmarterAuthenticatedNeverCachedWebView):
    """
    Render the vectorstore list view for the Smarter Workbench web console.

    This view displays all vectorstores available to the authenticated user as cards, providing a summary and quick access to vectorstore details.

    :param request: Django HTTP request object.
    :type request: WSGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    :returns: Rendered HTML page with a card for each vectorstore, or a 404 error page if the user is not authenticated.
    :rtype: HttpResponse

    .. seealso::

        :class:`VectorDatabase` for vectorstore metadata and retrieval.

    **Example usage**::

        GET /vectorstore/list/

    """

    template_path = "vectorstore/vectorstore_list.html"
    vectorstores: list[VectorDatabase] = []

    def get(self, request: WSGIRequest, *args, **kwargs):
        if request.user is None:
            logger.error("%s.get() Request user is None. This should not happen.", self.formatted_class_name)
            return SmarterHttpResponseNotFound(request=request, error_message="User is not authenticated")
        self.vectorstores = VectorDatabase.get_cached_vectorstores_for_user(request.user)  # type: ignore
        context = {
            "vectorstores": self.vectorstores,
        }
        return self.clean_http_response(request=request, template_path=self.template_path, context=context)


__all__ = ["VectorstoreManifestView", "VectorstoreListView"]
