# pylint: disable=W0613
"""
This module contains views to implement the Proxy.

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
from smarter.apps.proxy.models import Proxy
from smarter.common.helpers.console_helpers import formatted_json
from smarter.lib import logging
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
    SmarterHttpResponseServerError,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROXY_LOGGING])


class ProxyDetailView(DocsBaseView):
    """
    Renders the detail view for a Smarter dashboard proxy.

    This view renders a detailed manifest for a specific proxy, including its configuration and metadata, in YAML format. It is intended for authenticated users and provides error handling for missing or unsupported proxy kinds and names.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Keyword arguments, must include 'name' (proxy name) and 'kind' (proxy type).
    :type kwargs: dict

    :returns: Rendered HTML page with proxy manifest details, or a 404 error page if the proxy is not found or parameters are invalid.
    :rtype: HttpResponse

    .. note::

        The proxy name and kind must be provided and valid. Otherwise, a "not found" response is returned.

    .. seealso::

        :class:`Proxy` for proxy metadata retrieval.
        :class:`ApiV1CliDescribeApiView` for API details.

    **Example usage**::

        GET /proxy/detail/?name=my_proxy&kind=custom
    """

    template_path = "common/manifest_detail.html"
    proxy: Optional[Proxy] = None

    def get(self, request, *args, **kwargs) -> HttpResponse:
        """
        Handle GET requests to render the proxy manifest detail view.

        This method processes the incoming request to retrieve the
        specified proxy's manifest details and renders them in a
        user-friendly format. It performs validation on the provided proxy
        name and kind, retrieves the proxy metadata, and handles any
        errors that may arise during this process.

        Process:
        1. Extract and validate 'name' and 'kind' from kwargs.
        2. Retrieve the proxy metadata using the provided name and user context.
        3. If the proxy is found, call the API view to get the proxy details
        4. Convert the JSON response to YAML format for better readability.
        5. Render the proxy manifest detail template with the retrieved data.
        6. Handle any errors that occur during the process and return appropriate error responses.

        :param request: Django HTTP request object.
        :type request: ASGIRequest
        :param args: Additional positional arguments.
        :type args: tuple
        :param kwargs: Keyword arguments, must include 'name' (proxy name) and 'kind' (proxy type).
        :type kwargs: dict

        :returns: Rendered HTML page with proxy manifest details, or an error response if the proxy is not found or parameters are invalid.
        :rtype: HttpResponse
        """

        # to avoid potential circular import issues.
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews

        hashed_id = kwargs.pop("hashed_id")
        pk_id = Proxy.id_from_hashed_id(hashed_id) if hashed_id else None
        if not pk_id:
            logger.error("%s.get() - Invalid or missing hashed_id: %s", self.formatted_class_name, hashed_id)
            return SmarterHttpResponseNotFound(request=request, error_message="Proxy not found")

        try:
            self.proxy = Proxy.objects.get(id=pk_id, user_profile=self.user_profile)
            logger.debug(
                "%s.get() Found proxy with id %s for user %s.",
                self.formatted_class_name,
                pk_id,
                self.user_profile.user.username if self.user_profile else "unknown user",
            )
        except Proxy.DoesNotExist:
            try:
                if self.user_profile:

                    admin_user = UserProfile.admin_for_account(self.user_profile.account)
                    admin_user_profile = UserProfile.get_cached_object(user=admin_user)  # type: ignore
                    self.proxy = Proxy.objects.get(id=pk_id, user_profile=admin_user_profile)
                    logger.debug(
                        "%s.get() Found proxy with id %s for admin user %s.",
                        self.formatted_class_name,
                        pk_id,
                        admin_user if admin_user else "unknown admin user",
                    )
            except Proxy.DoesNotExist:
                try:
                    self.proxy = Proxy.objects.get(
                        id=pk_id, user_profile=smarter_cached_objects.smarter_admin_user_profile
                    )
                    logger.debug(
                        "%s.get() Found proxy with id %s for smarter admin user %s.",
                        self.formatted_class_name,
                        pk_id,
                        smarter_cached_objects.smarter_admin_user_profile.user,
                    )
                except Proxy.DoesNotExist:
                    pass
        if not self.proxy:
            logger.error(
                "%s.get() - Proxy with id %s not found for user %s or admin users.",
                self.formatted_class_name,
                pk_id,
                self.user_profile.user.username if self.user_profile else "unknown user",
            )
            return SmarterHttpResponseNotFound(request=request, error_message="Proxy not found")

        self.kind = SAMKinds.SECRET

        logger.debug(
            "%s.post() Rendering proxy detail view for %s, kwargs=%s.",
            self.formatted_class_name,
            self.proxy.name if self.proxy else "unknown proxy",
            kwargs,
        )
        kwargs.pop("name", None)
        kwargs["name"] = self.proxy.name if self.proxy else "unknown proxy"
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
            "page_title": self.proxy.name if self.proxy else "unknown proxy",
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
