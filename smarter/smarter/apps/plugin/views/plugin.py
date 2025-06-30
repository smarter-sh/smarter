# pylint: disable=W0613
"""
smarter.apps.plugin.views.plugin
This module contains views to implement the card-style list view
in the Smarter Dashboard.
"""
import logging
from typing import Optional

import yaml
from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import render

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.cli.views.describe import ApiV1CliDescribeApiView
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.docs.views.base import DocsBaseView
from smarter.apps.plugin.models import PluginMeta
from smarter.common.const import SMARTER_IS_INTERNAL_API_REQUEST
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import SmarterHttpResponseNotFound
from smarter.lib.django.view_helpers import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level <= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class PluginDetailView(DocsBaseView):
    """
    detail view for Smarter dashboard.
    """

    template_path = "plugin/manifest_detail.html"
    name: Optional[str] = None
    kwargs: Optional[dict] = None
    plugin: Optional[PluginMeta] = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        if self.user is None:
            logger.error("Request user is None. This should not happen.")
            return SmarterHttpResponseNotFound(request=request, error_message="User is not authenticated")
        self.name = kwargs.pop("name", None)
        self.kind = SAMKinds.str_to_kind(kwargs.pop("kind", None))
        if self.kind is None:
            logger.error("Plugin kind is required but not provided.")
            return SmarterHttpResponseNotFound(request=request, error_message="Plugin kind is required")
        if self.kind not in SAMKinds.all_plugins():
            logger.error("Plugin kind %s is not supported.", self.kind)
            return SmarterHttpResponseNotFound(
                request=request, error_message=f"Plugin kind {self.kind} is not supported"
            )
        if not self.name:
            logger.error("Plugin name is required but not provided.")
            return SmarterHttpResponseNotFound(request=request, error_message="Plugin name is required")
        self.plugin = PluginMeta.get_cached_plugin_by_name(user=self.user, name=self.name)

    def get(self, request, *args, **kwargs):
        if not self.plugin:
            logger.error("Plugin %s not found for user %s.", self.name, self.user.username)  # type: ignore[union-attr]
            return SmarterHttpResponseNotFound(request=request, error_message="Plugin not found")

        logger.info("Rendering connection detail view for %s of kind %s, kwargs=%s.", self.name, self.kind, kwargs)
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
            logger.error("self.template_path is not set.")
            return SmarterHttpResponseNotFound(request=request, error_message="Template path not set")
        return render(request, self.template_path, context=context)


class PluginListView(SmarterAuthenticatedNeverCachedWebView):
    """
    list view for smarter workbench web console. It generates cards for each
    plugin.
    """

    template_path = "plugin/plugin_list.html"
    plugins: list[PluginMeta]

    def get(self, request: WSGIRequest, *args, **kwargs):
        if self.user is None:
            logger.error("Request user is None. This should not happen.")
            return SmarterHttpResponseNotFound(request=request, error_message="User is not authenticated")
        self.plugins = PluginMeta.get_cached_plugins_for_user(self.user)
        context = {
            "plugins": self.plugins,
        }
        return self.clean_http_response(request=request, template_path=self.template_path, context=context)
