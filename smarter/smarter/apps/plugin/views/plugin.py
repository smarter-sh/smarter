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
from django.shortcuts import render

from smarter.apps.account.models import User
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.cli.views.describe import ApiV1CliDescribeApiView
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.docs.views.base import DocsBaseView
from smarter.apps.plugin.models import PluginMeta
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
    name: Optional[str] = None
    kwargs: Optional[dict] = None
    plugin: Optional[PluginMeta] = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        if not isinstance(request.user, User):
            logger.error("%s.setup() Request user is None. This should not happen.", self.formatted_class_name)
            return SmarterHttpResponseNotFound(request=request, error_message="User is not authenticated")
        name = kwargs.pop("name", None)
        self.name = rfc1034_compliant_to_snake(name) if name else None
        self.kind = SAMKinds.str_to_kind(kwargs.pop("kind", None))
        if self.kind is None:
            logger.error("%s.setup() Plugin kind is required but not provided.", self.formatted_class_name)
            return SmarterHttpResponseNotFound(request=request, error_message="Plugin kind is required")
        if self.kind not in SAMKinds.all_plugins():
            logger.error("%s.setup() Plugin kind %s is not supported.", self.formatted_class_name, self.kind)
            return SmarterHttpResponseNotFound(
                request=request, error_message=f"Plugin kind {self.kind} is not supported"
            )
        if not self.name:
            logger.error("%s.setup() Plugin name is required but not provided.", self.formatted_class_name)
            return SmarterHttpResponseNotFound(request=request, error_message="Plugin name is required")
        self.plugin = PluginMeta.get_cached_plugin_by_user_and_name(user=request.user, name=self.name)

    def get(self, request, *args, **kwargs):
        if not self.plugin:
            logger.error("%s.get() Plugin %s not found for user %s.", self.formatted_class_name, self.name, request.user.username)  # type: ignore[union-attr]
            return SmarterHttpResponseNotFound(request=request, error_message="Plugin not found")

        logger.debug(
            "%s.get() Rendering plugin detail view for %s of kind %s, kwargs=%s.",
            self.formatted_class_name,
            self.name,
            self.kind,
            kwargs,
        )
        # get_brokered_json_response() adds self.kind to kwargs, so we remove it here.
        # TypeError: smarter.apps.api.v1.cli.views.describe.View.as_view.<locals>.view() got multiple values for keyword argument 'kind'
        kwargs.pop("kind", None)
        kwargs["name"] = self.name
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
            logger.error("%s.setup() self.template_path is not set.", self.formatted_class_name)
            return SmarterHttpResponseNotFound(request=request, error_message="Template path not set")
        return render(request, self.template_path, context=context)


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
            request.user.username if request.user else "None",
            args,
            kwargs,
        )
        if request.user is None or isinstance(request.user, AnonymousUser):
            logger.error(
                "%s.get() Request user is None or anonymous. This should not happen.", self.formatted_class_name
            )
            return SmarterHttpResponseNotFound(request=request, error_message="User is not authenticated")
        self.plugins = PluginMeta.get_cached_plugins_for_user_profile_id(self.user_profile.id)  # type: ignore[attr-defined]
        context = {"plugins": self.plugins, "smarter_admin": smarter_cached_objects.smarter_admin}
        return self.clean_http_response(request=request, template_path=self.template_path, context=context)
