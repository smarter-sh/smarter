# pylint: disable=W0613
"""
smarter.apps.plugin.views.plugin
This module contains views to implement the card-style list view
in the Smarter Dashboard.
"""

import logging
from typing import Optional

import yaml
from django.contrib.auth.models import AnonymousUser
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import render

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.api.v1.cli.views.describe import ApiV1CliDescribeApiView
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.docs.views.base import DocsBaseView
from smarter.apps.plugin.models import PluginMeta
from smarter.common.helpers.console_helpers import formatted_json
from smarter.common.utils import is_authenticated_request, rfc1034_compliant_to_snake
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
    SmarterHttpResponseServerError,
)
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class PluginDetailView(DocsBaseView):
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

    template_path = "plugin/manifest_detail.html"
    plugin: Optional[PluginMeta] = None

    def get(self, request, *args, **kwargs) -> HttpResponse:
        """
        Handle GET requests to render the plugin manifest detail view.
        This method processes the incoming request to retrieve the
        specified plugin's manifest details and renders them in a
        user-friendly format. It performs validation on the provided plugin
        name and kind, retrieves the plugin metadata, and handles any
        errors that may arise during this process.

        Process:
        1. Extract and validate 'name' and 'kind' from kwargs.
        2. Retrieve the plugin metadata using the provided name and user context.
        3. If the plugin is found, call the API view to get the plugin details        4. Convert the JSON response to YAML format for better readability.
        5. Render the plugin manifest detail template with the retrieved data.
        6. Handle any errors that occur during the process and return appropriate error responses.

        :param request: Django HTTP request object.
        :type request: WSGIRequest
        :param args: Additional positional arguments.
        :type args: tuple
        :param kwargs: Keyword arguments, must include 'name' (plugin name) and 'kind' (plugin type).
        :type kwargs: dict

        :returns: Rendered HTML page with plugin manifest details, or an error response if the plugin is not found or parameters are invalid.
        :rtype: HttpResponse
        """

        # to avoid potential circular import issues.
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews

        name = kwargs.pop("name", None)
        self.name = rfc1034_compliant_to_snake(name) if name else None
        self.kind = SAMKinds.str_to_kind(kwargs.pop("kind", None))
        if self.kind is None:
            logger.error("%s.setup() Plugin kind is required but not provided.", self.formatted_class_name)
            return SmarterHttpResponseNotFound(request=request, error_message="Plugin kind is required")
        if not self.kind or self.kind not in SAMKinds.all_plugins():
            logger.error("%s.setup() Plugin kind %s is not supported.", self.formatted_class_name, self.kind)
            return SmarterHttpResponseNotFound(
                request=request, error_message=f"Plugin kind {self.kind} is not supported"
            )
        if not self.name:
            logger.error("%s.setup() Plugin name is required but not provided.", self.formatted_class_name)
            return SmarterHttpResponseNotFound(request=request, error_message="Plugin name is required")
        self.plugin = PluginMeta.get_cached_object(name=self.name, user=request.user)  # type: ignore[attr-defined]
        if not self.plugin:
            logger.error(
                "%s.setup() Plugin with name %s and kind %s not found for user %s.",
                self.formatted_class_name,
                self.name,
                self.kind,
                request.user.username if is_authenticated_request(request) else "Anonymous",  # type: ignore[union-attr]
            )
            return SmarterHttpResponseNotFound(request=request, error_message="Plugin not found")

        logger.debug(
            "%s.post() Rendering plugin detail view for %s of kind %s, kwargs=%s.",
            self.formatted_class_name,
            self.name,
            self.kind,
            kwargs,
        )
        kwargs.pop("name", None)
        kwargs.pop("kind", None)
        kwargs["name"] = self.name
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


class PluginListView(SmarterAuthenticatedNeverCachedWebView):
    """
    Render the plugin list view for the Smarter Workbench web console.

    This view displays all plugins available to the authenticated user as cards, providing a quick overview and access to plugin details.

    :param request: Django HTTP request object.
    :type request: WSGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Additional keyword arguments.
    :type kwargs: dict

    :returns: Rendered HTML page with a card for each plugin, or a 404 error page if the user is not authenticated.
    :rtype: HttpResponse
    """

    template_path = "plugin/plugin_list.html"
    plugins: list[PluginMeta]

    def get(self, request: WSGIRequest, *args, **kwargs):
        logger.debug(
            "%s.get() Rendering plugin list view for user %s with args=%s, kwargs=%s.",
            self.formatted_class_name,
            request.user.username if request.user else "None",  # type: ignore[union-attr]
            args,
            kwargs,
        )
        if request.user is None or isinstance(request.user, AnonymousUser):
            logger.error(
                "%s.get() Request user is None or anonymous. This should not happen.", self.formatted_class_name
            )
            return SmarterHttpResponseNotFound(request=request, error_message="User is not authenticated")
        self.plugins = PluginMeta.get_cached_plugins_for_user_profile_id(user_profile_id=self.user_profile.id)  # type: ignore[attr-defined]
        context = {"plugins": self.plugins, "smarter_admin": smarter_cached_objects.smarter_admin}
        return self.clean_http_response(request=request, template_path=self.template_path, context=context)
