"""
Views for provider-related pages in the Smarter Workbench web console.
"""

import logging
from typing import Optional

import yaml
from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import render

from smarter.apps.account.models import User
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.cli.views.describe import ApiV1CliDescribeApiView
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.docs.views.base import DocsBaseView
from smarter.apps.provider.models import Provider
from smarter.common.const import SMARTER_IS_INTERNAL_API_REQUEST
from smarter.common.utils import rfc1034_compliant_to_snake
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import SmarterHttpResponseNotFound
from smarter.lib.django.view_helpers import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


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
    name: Optional[str] = None
    kwargs: Optional[dict] = None
    provider: Optional[Provider] = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        if not isinstance(request.user, User):
            logger.error("Request user instance of type %s is not a User. This should not happen.", type(request.user))
            return SmarterHttpResponseNotFound(request=request, error_message="User is not authenticated")
        name = kwargs.pop("name", None)
        self.name = rfc1034_compliant_to_snake(name) if name else None
        if not isinstance(self.name, str):
            logger.error("Provider name should be type str but received %s. This is a bug.", type(self.name))
            return SmarterHttpResponseNotFound(request=request, error_message="Provider name is required")
        self.provider = Provider.get_cached_provider_by_user_and_name(user=request.user, name=self.name)

    def get(self, request, *args, **kwargs):
        if not self.provider:
            logger.error("Provider %s not found for user %s.", self.name, request.user.username)  # type: ignore[union-attr]
            return SmarterHttpResponseNotFound(request=request, error_message="Provider not found")

        logger.info("Rendering connection detail view for %s of kind %s, kwargs=%s.", self.name, self.kind, kwargs)
        # get_brokered_json_response() adds self.kind to kwargs, so we remove it here.
        # TypeError: smarter.apps.api.v1.cli.views.describe.View.as_view.<locals>.view() got multiple values for keyword argument 'kind'
        kwargs["name"] = self.name
        self.kind = SAMKinds.PROVIDER
        setattr(request, SMARTER_IS_INTERNAL_API_REQUEST, True)
        view = ApiV1CliDescribeApiView.as_view()
        json_response = self.get_brokered_json_response(
            reverse_name=ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.describe,
            view=view,
            request=request,
            *args,
            **kwargs,
        )

        yaml_response = yaml.dump(json_response, default_flow_style=False)
        context = {
            "manifest": yaml_response,
            "page_title": self.name,
        }
        if not self.template_path:
            logger.error("self.template_path is not set.")
            return SmarterHttpResponseNotFound(request=request, error_message="Template path not set")
        return render(request, self.template_path, context=context)


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
    providers: list[Provider]

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
        self.providers = Provider.get_cached_providers_for_user(request.user)
        context = {
            "provider_list": {"providers": self.providers, "smarter_admin": smarter_cached_objects.smarter_admin}
        }
        return self.clean_http_response(request=request, template_path=self.template_path, context=context)
