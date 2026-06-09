# pylint: disable=W0613
"""
This module contains views to implement the Connection.

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
from smarter.apps.connection.models.api_connection import ApiConnection
from smarter.apps.connection.models.sql_connection import SqlConnection
from smarter.apps.docs.views.base import DocsBaseView
from smarter.common.helpers.console_helpers import formatted_json
from smarter.lib import logging
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
    SmarterHttpResponseServerError,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CONNECTION_LOGGING])


class ApiConnectionDetailView(DocsBaseView):
    """
    Renders the detail view for a Smarter dashboard ApiConnection.

    This view renders a detailed manifest for a specific ApiConnection,
    including its configuration and metadata, in YAML format. It is intended for
    authenticated users and provides error handling for missing or unsupported
    connection kinds and names.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Keyword arguments, must include 'name' (connection name) and 'kind' (connection type).
    :type kwargs: dict

    :returns: Rendered HTML page with connection manifest details, or a 404 error page if the connection is not found or parameters are invalid.
    :rtype: HttpResponse

    .. note::

        The connection name and kind must be provided and valid. Otherwise, a "not found" response is returned.

    .. seealso::

        :class:`ApiConnection` for connection metadata retrieval.
        :class:`ApiV1CliDescribeApiView` for API details.

    **Example usage**::

        GET /connections/connection/api-connection/my-connection/
    """

    template_path = "common/manifest_detail.html"
    connection: Optional[ApiConnection] = None

    @property
    def formatted_class_name(self) -> str:
        """Helper method to get the formatted class name for logging."""
        return logging.formatted_text(f"{__name__}.{ApiConnectionDetailView.__name__}")

    def get(self, request, *args, **kwargs) -> HttpResponse:
        """
        Handle GET requests to render the connection manifest detail view.

        This method processes the incoming request to retrieve the
        specified connection's manifest details and renders them in a
        user-friendly format. It performs validation on the provided connection
        name and kind, retrieves the connection metadata, and handles any
        errors that may arise during this process.

        Process:
        1. Extract and validate 'name' and 'kind' from kwargs.
        2. Retrieve the connection metadata using the provided name and user context.
        3. If the connection is found, call the API view to get the connection details
        4. Convert the JSON response to YAML format for better readability.
        5. Render the connection manifest detail template with the retrieved data.
        6. Handle any errors that occur during the process and return appropriate error responses.

        :param request: Django HTTP request object.
        :type request: ASGIRequest
        :param args: Additional positional arguments.
        :type args: tuple
        :param kwargs: Keyword arguments, must include 'name' (connection name) and 'kind' (connection type).
        :type kwargs: dict

        :returns: Rendered HTML page with connection manifest details, or an error response if the connection is not found or parameters are invalid.
        :rtype: HttpResponse
        """
        logger.debug(
            "%s.get() called with kwargs: %s for user %s.",
            self.formatted_class_name,
            kwargs,
            self.user_profile.user.username if self.user_profile else "unknown user",
        )

        # to avoid potential circular import issues.
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews

        hashed_id = kwargs.pop("hashed_id")
        pk_id = ApiConnection.id_from_hashed_id(hashed_id) if hashed_id else None
        if not pk_id:
            logger.warning(
                "%s.get() - Invalid hashed_id '%s' provided. Returning 404.",
                self.formatted_class_name,
                hashed_id,
            )
            return SmarterHttpResponseNotFound(request=request, error_message="Invalid connection identifier")
        try:
            self.connection = ApiConnection.objects.get(pk=pk_id, user_profile=self.user_profile)
            logger.debug(
                "%s.get() Found ApiConnection with hashed_id '%s' for user %s.",
                self.formatted_class_name,
                hashed_id,
                self.user_profile.user.username if self.user_profile else "unknown user",
            )
        except ApiConnection.DoesNotExist:
            try:
                if self.user_profile:
                    admin_user = UserProfile.admin_for_account(self.user_profile.account)
                    admin_user_profile = UserProfile.get_cached_object(user=admin_user)  # type: ignore
                    self.connection = ApiConnection.objects.get(pk=pk_id, user_profile=admin_user_profile)
                    logger.debug(
                        "%s.get() Found ApiConnection with hashed_id '%s' for admin user %s.",
                        self.formatted_class_name,
                        hashed_id,
                        admin_user if admin_user else "unknown admin user",
                    )
            except ApiConnection.DoesNotExist:
                try:
                    self.connection = ApiConnection.objects.get(
                        pk=pk_id, user_profile=smarter_cached_objects.smarter_admin_user_profile
                    )
                    logger.debug(
                        "%s.get() Found ApiConnection with hashed_id '%s' for smarter admin user %s.",
                        self.formatted_class_name,
                        hashed_id,
                        smarter_cached_objects.smarter_admin_user_profile.user,
                    )
                except ApiConnection.DoesNotExist:
                    pass
        if not isinstance(self.connection, ApiConnection):
            logger.warning(
                "%s.get() - ApiConnection with hashed_id '%s' not found for user %s, nor the account admin %s, nor the Smarter admin %s. Returning 404.",
                self.formatted_class_name,
                hashed_id,
                self.user_profile.user if self.user_profile else "unknown user",
                admin_user if admin_user else "unknown admin user",
                smarter_cached_objects.smarter_admin_user_profile.user,
            )
            return SmarterHttpResponseNotFound(request=request, error_message="ApiConnection not found")

        logger.debug(
            "%s.post() Rendering connection detail view for %s, kwargs=%s.",
            self.formatted_class_name,
            self.connection.name if self.connection else "unknown connection",
            kwargs,
        )
        kwargs["name"] = self.connection.name if self.connection else "unknown connection"
        kwargs["kind"] = SAMKinds.API_CONNECTION.value
        self.kind = SAMKinds.API_CONNECTION
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
            "page_title": self.connection.name if self.connection else "unknown connection",
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


class SqlConnectionDetailView(DocsBaseView):
    """
    Renders the detail view for a Smarter dashboard SqlConnection.

    This view renders a detailed manifest for a specific SqlConnection,
    including its configuration and metadata, in YAML format. It is intended for
    authenticated users and provides error handling for missing or unsupported
    connection kinds and names.

    :param request: Django HTTP request object.
    :type request: ASGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Keyword arguments, must include 'name' (connection name) and 'kind' (connection type).
    :type kwargs: dict

    :returns: Rendered HTML page with connection manifest details, or a 404 error page if the connection is not found or parameters are invalid.
    :rtype: HttpResponse

    .. note::

        The connection name and kind must be provided and valid. Otherwise, a "not found" response is returned.

    .. seealso::

        :class:`Connection` for connection metadata retrieval.
        :class:`ApiV1CliDescribeApiView` for API details.

    **Example usage**::

        GET /connections/connection/sql-connection/my-connection/
    """

    template_path = "common/manifest_detail.html"
    connection: Optional[SqlConnection] = None

    @property
    def formatted_class_name(self) -> str:
        """Helper method to get the formatted class name for logging."""
        return logging.formatted_text(f"{__name__}.{SqlConnectionDetailView.__name__}")

    def get(self, request, *args, **kwargs) -> HttpResponse:
        """
        Handle GET requests to render the connection manifest detail view.

        This method processes the incoming request to retrieve the
        specified connection's manifest details and renders them in a
        user-friendly format. It performs validation on the provided connection
        name and kind, retrieves the connection metadata, and handles any
        errors that may arise during this process.

        Process:
        1. Extract and validate 'name' and 'kind' from kwargs.
        2. Retrieve the connection metadata using the provided name and user context.
        3. If the connection is found, call the API view to get the connection details
        4. Convert the JSON response to YAML format for better readability.
        5. Render the connection manifest detail template with the retrieved data.
        6. Handle any errors that occur during the process and return appropriate error responses.

        :param request: Django HTTP request object.
        :type request: ASGIRequest
        :param args: Additional positional arguments.
        :type args: tuple
        :param kwargs: Keyword arguments, must include 'name' (connection name) and 'kind' (connection type).
        :type kwargs: dict

        :returns: Rendered HTML page with connection manifest details, or an error response if the connection is not found or parameters are invalid.
        :rtype: HttpResponse
        """
        logger.debug(
            "%s.get() called with kwargs: %s for user %s.",
            self.formatted_class_name,
            kwargs,
            self.user_profile.user.username if self.user_profile else "unknown user",
        )

        # to avoid potential circular import issues.
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews

        hashed_id = kwargs.pop("hashed_id")
        pk_id = SqlConnection.id_from_hashed_id(hashed_id) if hashed_id else None
        if not pk_id:
            logger.warning(
                "%s.get() - Invalid hashed_id '%s' provided. Returning 404.",
                self.formatted_class_name,
                hashed_id,
            )
            return SmarterHttpResponseNotFound(request=request, error_message="Invalid connection identifier")
        admin_user = None
        try:
            self.connection = SqlConnection.objects.get(pk=pk_id, user_profile=self.user_profile)
            print(self.connection.hashed_id)
            logger.debug(
                "%s.get() Found SqlConnection with hashed_id '%s' for user %s.",
                self.formatted_class_name,
                hashed_id,
                self.user_profile.user.username if self.user_profile else "unknown user",
            )
        except SqlConnection.DoesNotExist:
            try:
                if self.user_profile:

                    admin_user = UserProfile.admin_for_account(self.user_profile.account)
                    admin_user_profile = UserProfile.get_cached_object(user=admin_user)  # type: ignore
                    self.connection = SqlConnection.objects.get(pk=pk_id, user_profile=admin_user_profile)
                    logger.debug(
                        "%s.get() Found SqlConnection with hashed_id '%s' for admin user %s.",
                        self.formatted_class_name,
                        hashed_id,
                        admin_user if admin_user else "unknown admin user",
                    )
            except SqlConnection.DoesNotExist:
                try:
                    self.connection = SqlConnection.objects.get(
                        pk=pk_id, user_profile=smarter_cached_objects.smarter_admin_user_profile
                    )
                    logger.debug(
                        "%s.get() Found SqlConnection with hashed_id '%s' for smarter admin user %s.",
                        self.formatted_class_name,
                        hashed_id,
                        smarter_cached_objects.smarter_admin_user_profile.user,
                    )
                except SqlConnection.DoesNotExist:
                    pass

        if not isinstance(self.connection, SqlConnection):
            logger.warning(
                "%s.get() - SqlConnection with hashed_id '%s' not found for user %s, nor the account admin %s, nor the Smarter admin %s. Returning 404.",
                self.formatted_class_name,
                hashed_id,
                self.user_profile.user if self.user_profile else "unknown user",
                admin_user if admin_user else "unknown admin user",
                smarter_cached_objects.smarter_admin_user_profile.user,
            )
            return SmarterHttpResponseNotFound(request=request, error_message="SqlConnection not found")

        logger.debug(
            "%s.post() Rendering connection detail view for %s, kwargs=%s.",
            self.formatted_class_name,
            self.connection.name if self.connection else "unknown connection",
            kwargs,
        )
        kwargs.pop("name", None)
        kwargs["name"] = self.connection.name if self.connection else "unknown connection"
        kwargs["kind"] = SAMKinds.SQL_CONNECTION.value
        self.kind = SAMKinds.SQL_CONNECTION
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
            "page_title": self.connection.name if self.connection else "unknown connection",
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
