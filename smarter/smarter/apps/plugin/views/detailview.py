# pylint: disable=W0613
"""
This module contains views to implement the Plugin.

card-style detail view in the Smarter Dashboard.
"""

from typing import Optional

import yaml
from django.http import HttpResponse
from django.shortcuts import render

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.api.v1.cli.views.describe import ApiV1CliDescribeApiView
from smarter.apps.docs.views.base import DocsBaseView
from smarter.apps.plugin.models import PluginMeta
from smarter.common.helpers.console_helpers import formatted_json
from smarter.common.utils import is_authenticated_request
from smarter.lib import logging
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
    SmarterHttpResponseServerError,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])


class PluginDetailView(DocsBaseView):
    """
    Renders the detail view for a Smarter dashboard plugin.

    This view renders a detailed manifest for a specific plugin, including its configuration and metadata, in YAML format. It is intended for authenticated users and provides error handling for missing or unsupported plugin kinds and names.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Keyword arguments, must include 'hashed_id' (plugin hashed ID) and 'kind' (plugin type).
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

    template_path = "common/manifest_detail.html"
    plugin: Optional[PluginMeta] = None

    @property
    def formatted_class_name(self):
        class_name = f"{__name__}.{PluginDetailView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

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
        3. If the plugin is found, call the API view to get the plugin details
        4. Convert the JSON response to YAML format for better readability.
        5. Render the plugin manifest detail template with the retrieved data.
        6. Handle any errors that occur during the process and return appropriate error responses.

        :param request: Django HTTP request object.
        :type request: ASGIRequest
        :param args: Additional positional arguments.
        :type args: tuple
        :param kwargs: Keyword arguments, must include 'name' (plugin name) and 'kind' (plugin type).
        :type kwargs: dict

        :returns: Rendered HTML page with plugin manifest details, or an error response if the plugin is not found or parameters are invalid.
        :rtype: HttpResponse
        """
        logger.debug(
            "%s.get() called with args=%s, kwargs=%s",
            self.formatted_class_name,
            args,
            kwargs,
        )

        # to avoid potential circular import issues.
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews

        hashed_id = kwargs.pop("hashed_id", None)
        pk_id = PluginMeta.id_from_hashed_id(hashed_id) if hashed_id else None
        if not pk_id:
            logger.error("%s.get() Invalid or missing hashed_id: %s", self.formatted_class_name, hashed_id)
            return SmarterHttpResponseNotFound(request=request, error_message="Invalid plugin identifier")

        try:
            self.plugin = PluginMeta.objects.get(id=pk_id, user_profile=self.user_profile)
            logger.debug(
                "%s.get() Found plugin with name %s and kind %s for user %s.",
                self.formatted_class_name,
                self.plugin.name,
                self.plugin.kind,
                self.user_profile if self.user_profile else "unknown user",
            )
        except PluginMeta.DoesNotExist:
            try:
                if self.user_profile:

                    admin_user = UserProfile.admin_for_account(self.user_profile.account)
                    admin_user_profile = UserProfile.get_cached_object(user=admin_user)  # type: ignore
                    self.plugin = PluginMeta.objects.get(id=pk_id, user_profile=admin_user_profile)
                    logger.debug(
                        "%s.get() Found plugin with name %s and kind %s for admin user %s.",
                        self.formatted_class_name,
                        self.plugin.name,
                        self.plugin.kind,
                        admin_user if admin_user else "unknown admin user",
                    )
            except PluginMeta.DoesNotExist:
                try:
                    self.plugin = PluginMeta.objects.get(
                        id=pk_id, user_profile=smarter_cached_objects.smarter_admin_user_profile
                    )
                    logger.debug(
                        "%s.get() Found plugin with name %s and kind %s for smarter admin user.",
                        self.formatted_class_name,
                        self.plugin.name,
                        self.plugin.kind,
                    )
                except PluginMeta.DoesNotExist:
                    pass
        if not self.plugin:
            logger.error(
                "%s.get() Plugin with hashed_id %s not found for user %s or admin users.",
                self.formatted_class_name,
                hashed_id,
                self.user_profile if self.user_profile else "unknown user",
            )
            return SmarterHttpResponseNotFound(request=request, error_message="Plugin not found")

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
        self.name = self.plugin.name
        self.kind = self.plugin.kind
        kwargs["name"] = self.name
        kwargs["kind"] = self.kind.value if self.kind else None
        view = ApiV1CliDescribeApiView.as_view()
        logger.debug(
            "%s.get() Calling API view to get plugin details for %s of kind %s, args=%s, kwargs=%s.",
            self.formatted_class_name,
            self.name,
            self.kind,
            args,
            kwargs,
        )
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
            )
            return SmarterHttpResponseServerError(request=request, error_message="Error rendering manifest page")
        return response
