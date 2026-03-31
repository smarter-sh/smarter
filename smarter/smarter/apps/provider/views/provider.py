"""
Views for provider-related pages in the Smarter Workbench web console.
"""

import logging
from typing import Optional, Sequence

import yaml
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from smarter.apps.account.models import User
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.cli.views.describe import ApiV1CliDescribeApiView
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.docs.views.base import DocsBaseView
from smarter.apps.provider.models import Provider
from smarter.common.helpers.logger_helpers import formatted_json
from smarter.common.utils import rfc1034_compliant_to_snake
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
    SmarterHttpResponseServerError,
)
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class ProviderDetailView(DocsBaseView):
    """
    Renders the detail view for a Smarter dashboard plugin.

    This view renders a detailed manifest for a specific plugin, including its configuration and metadata, in YAML format. It is intended for authenticated users and provides error handling for missing or unsupported plugin kinds and names.

    :param request: Django HTTP request object.
    :type request: WSGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Keyword arguments, must include 'name' (plugin name) and 'kind' (plugin type).
    :type kwargs: dict

    :returns: Rendered HTML page with plugin manifest details, or a 404 error page if the plugin is not found or parameters are invalid.
    :rtype: HttpResponse

    .. note::

        The plugin name and kind must be provided and valid. Otherwise, a "not found" response is returned.

    .. seealso::

        :class:`PluginMeta` for plugin metadata retrieval.
        :class:`ApiV1CliDescribeApiView` for API details.

    **Example usage**::

        GET /plugin/detail/?name=my_plugin&kind=custom

    """

    template_path = "provider/manifest_detail.html"
    provider: Optional[Provider] = None

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Handle GET requests to render the provider manifest detail view.
        This method processes the incoming request to retrieve the
        specified provider's manifest details and renders them in a
        user-friendly format. It performs validation on the provided provider
        name and kind, retrieves the provider metadata, and handles any
        errors that may arise during this process.

        Process:
        1. Extract and validate 'name' and 'kind' from kwargs.
        2. Retrieve the provider metadata using the provided name and user context.
        3. If the provider is found, call the API view to get the provider details
        4. Convert the JSON response to YAML format for better readability.
        5. Render the provider manifest detail template with the retrieved data.
        6. Handle any errors that occur during the process and return appropriate error responses.

        :param request: Django HTTP request object.
        :type request: WSGIRequest
        :param args: Additional positional arguments.
        :type args: tuple
        :param kwargs: Keyword arguments, must include 'name' (provider name) and 'kind' (provider type).
        :type kwargs: dict

        :returns: Rendered HTML page with provider manifest details, or an error response if the provider is not found or parameters are invalid.
        :rtype: HttpResponse
        """

        if not isinstance(request.user, User):
            logger.error("Request user instance of type %s is not a User. This should not happen.", type(request.user))
            return SmarterHttpResponseNotFound(request=request, error_message="User is not authenticated")
        name = kwargs.pop("name", None)
        self.name = rfc1034_compliant_to_snake(name) if name else None
        if not isinstance(self.name, str):
            logger.error("Provider name should be type str but received %s. This is a bug.", type(self.name))
            return SmarterHttpResponseNotFound(request=request, error_message="Provider name is required")
        self.provider = Provider.get_cached_provider_by_user_and_name(user=request.user, name=self.name)

        if not self.provider:
            logger.error("%s.post() Provider %s not found for user %s.", self.formatted_class_name, self.name, request.user.username)  # type: ignore[union-attr]
            return SmarterHttpResponseNotFound(request=request, error_message="Provider not found")

        logger.debug(
            "%s.post() Rendering provider detail view for %s of kind %s, kwargs=%s.",
            self.formatted_class_name,
            self.name,
            self.kind,
            kwargs,
        )
        # get_brokered_json_response() adds self.kind to kwargs, so we remove it here.
        # TypeError: smarter.apps.api.v1.cli.views.describe.View.as_view.<locals>.view() got multiple values for keyword argument 'kind'
        kwargs["name"] = self.name
        self.kind = SAMKinds.PROVIDER
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
                exec_info=True,
            )
            return SmarterHttpResponseServerError(request=request, error_message="Error rendering manifest page")
        return response


class ProviderListView(SmarterAuthenticatedNeverCachedWebView):
    """
    Render the provider list view for the Smarter Workbench web console.

    This view displays all providers available to the authenticated user as cards, providing a quick overview and access to provider details.

    :param request: Django HTTP request object.
    :type request: WSGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    :returns: Rendered HTML page with a card for each provider, or a 404 error page if the user is not authenticated.
    :rtype: HttpResponse


    """

    template_path = "provider/provider_list.html"
    providers: Sequence[Provider]

    def get(self, request: WSGIRequest, *args, **kwargs):
        self.smarter_request = request
        if not isinstance(request.user, User):
            logger.error(
                "%s.get() Request user %s %sis not an instance of User. This is a bug.",
                self.formatted_class_name,
                request.user,
                type(request.user),
            )
            return SmarterHttpResponseNotFound(request=request, error_message="User is not authenticated")
        self.providers = Provider.get_cached_providers_for_user(user=request.user)
        context = {
            "provider_list": {"providers": self.providers, "smarter_admin": smarter_cached_objects.smarter_admin}
        }
        return self.clean_http_response(request=request, template_path=self.template_path, context=context)
