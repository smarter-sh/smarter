"""
smarter.lib.drf.middleware
==========================

Middleware for Smarter token authentication using SmarterTokenAuthentication.

This module provides middleware for authenticating API requests using Knox tokens and the
SmarterTokenAuthentication backend. It supports both synchronous and asynchronous request handling,
performs early API endpoint filtering, validates token lifetimes, and integrates with Django signals
for authentication events. Structured logging is used throughout for observability, and the middleware
is compatible with Django's MiddlewareMixin.

Features
--------
- Early API endpoint filtering to minimize unnecessary authentication checks
- Knox token authentication for secure API access
- Token lifetime validation against configurable maximum age
- Structured logging for authentication events and errors
- Signal dispatching for authentication request, success, and failure
- Async-compatible middleware behavior for modern Django deployments

Classes
-------
.. autosummary::
   :toctree:

   SmarterTokenAuthenticationMiddleware

Signals
-------
- ``smarter_token_authentication_request``: Emitted when a token authentication attempt is made.
- ``smarter_token_authentication_success``: Emitted on successful authentication.
- ``smarter_token_authentication_failure``: Emitted on authentication failure.

Exceptions
----------
- ``SmarterTokenAuthenticationError``: Raised on authentication errors.

Dependencies
------------
- Django
- Django REST Framework
- Knox
- asgiref
- smarter.common, smarter.lib, and related internal modules
"""

from __future__ import annotations

import inspect
import traceback
from collections.abc import Awaitable
from datetime import timedelta
from http import HTTPStatus
from typing import Optional

from asgiref.sync import markcoroutinefunction, sync_to_async
from django.contrib.auth import login
from django.http import HttpResponseBase
from django.utils import timezone
from knox.settings import knox_settings
from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.mixins import SmarterHelperMixin, SmarterMiddlewareMixin
from smarter.common.utils import mask_string
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonErrorResponse

from .models import SmarterAuthToken
from .signals import (
    smarter_token_authentication_failure,
    smarter_token_authentication_request,
    smarter_token_authentication_success,
)
from .token_authentication import (
    SmarterAnonymousUser,
    SmarterTokenAuthentication,
    SmarterTokenAuthenticationError,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MIDDLEWARE_LOGGING])

if waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_SMARTER_TOKEN_AUTH):
    logger.debug(
        "%s is %s",
        formatted_text(__name__ + ".SmarterTokenAuthenticationMiddleware"),
        SmarterHelperMixin().formatted_state_ready,
    )
else:
    logger.debug(
        "%s is %s. Enable with Django waffle in the admin console.",
        formatted_text(__name__ + ".SmarterTokenAuthenticationMiddleware"),
        SmarterHelperMixin().formatted_state_not_ready,
    )


class SmarterTokenAuthenticationMiddleware(SmarterMiddlewareMixin):
    """
    Middleware for token authentication using SmarterTokenAuthentication.
    """

    sync_capable = True
    async_capable = True

    @property
    def formatted_class_name(self) -> str:
        return formatted_text(f"{__name__}.{self.__class__.__name__}")

    def __call__(self, request: Request) -> HttpResponseBase | Awaitable[HttpResponseBase]:

        if self.async_mode:
            return self.__acall__(request)

        logger.debug("%s.__call__(): Request received: %s %s", self.formatted_class_name, request.method, request.path)

        return self.process_request(request)

    async def __acall__(self, request: Request):

        logger.debug("%s.__acall__(): Request received: %s %s", self.formatted_class_name, request.method, request.path)
        return await sync_to_async(self.process_request)(request)

    def process_request(self, request: Request):

        if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_SMARTER_TOKEN_AUTH):
            return self.get_response(request)

        request = self.ensure_request_user(request)

        url = self.smarter_build_absolute_uri(request)
        if not isinstance(url, str):
            raise ValueError("Failed to build request URL.")

        logger.debug("%s processing request: %s", self.formatted_class_name, url)

        if not self.is_api_request(url):
            logger.debug("%s skipping non-api request", self.formatted_class_name)
            return self.get_response(request)

        if getattr(request, "auth", None) is not None:
            logger.debug("%s request already authenticated", self.formatted_class_name)
            return self.get_response(request)

        authorization_header = self.get_authorization_header(request)

        token = self.extract_token(authorization_header)

        if not token:
            logger.debug("%s no token authentication detected", self.formatted_class_name)
            return self.get_response(request)

        masked_token = mask_string(string=token)

        smarter_token_authentication_request.send(
            sender=self.__class__,
            token=masked_token,
            url=url,
        )

        try:

            user, auth_obj = self.authenticate_request(request)
            self.validate_token_lifetime(user=user, auth_obj=auth_obj)
            request.user = user or SmarterAnonymousUser()
            login(request, request.user, backend="django.contrib.auth.backends.ModelBackend")  # type: ignore

            smarter_token_authentication_success.send(
                sender=self.__class__,
                user=request.user,
                token=masked_token,
            )

            logger.info("%s authenticated user=%s", self.formatted_class_name, request.user)

        except AuthenticationFailed as auth_failed:

            return self.handle_authentication_failure(
                request=request,
                token=masked_token,
                exc=auth_failed,
            )

        logger.debug("%s authentication completed", self.formatted_class_name)

        return self.get_response(request)

    @staticmethod
    def is_api_request(url: str) -> bool:
        return SmarterValidator.is_api_endpoint(url)

    @staticmethod
    def get_authorization_header(request: Request) -> str:

        auth_header = get_authorization_header(request)

        if isinstance(auth_header, bytes):
            return auth_header.decode()
        if isinstance(auth_header, (bytes, bytearray)):
            return auth_header.decode()
        if isinstance(auth_header, memoryview):
            return auth_header.tobytes().decode()
        if isinstance(auth_header, str):
            return auth_header
        return ""

    @staticmethod
    def get_auth_prefix() -> str:

        prefix = knox_settings.AUTH_HEADER_PREFIX

        if isinstance(prefix, bytes):
            return prefix.decode()

        return str(prefix)

    def extract_token(self, authorization_header: str) -> str | None:
        """
        Extract token from Authorization header.
        """

        if not authorization_header:
            return None

        auth_parts = authorization_header.split()

        if len(auth_parts) != 2:
            return None

        auth_prefix, token = auth_parts

        expected_prefix = self.get_auth_prefix()

        if auth_prefix.lower() != expected_prefix.lower():
            return None

        logger.debug("%s detected token authentication token=%s", self.formatted_class_name, mask_string(token))

        return token

    @staticmethod
    def ensure_request_user(request: Request) -> Request:

        if not hasattr(request, "user") or request.user is None:
            request.user = SmarterAnonymousUser()

        return request

    @staticmethod
    def authenticate_request(request: Request):

        request.auth = SmarterTokenAuthentication()

        user_auth_tuple = request.auth.authenticate(request)

        if not user_auth_tuple:
            raise AuthenticationFailed("Authentication backend did not return a user.")

        user, auth_obj = user_auth_tuple

        if not user:
            raise AuthenticationFailed("Authentication backend returned an empty user.")

        return user, auth_obj

    def validate_token_lifetime(
        self,
        user,
        auth_obj,
    ) -> None:
        """
        Warn on tokens exceeding configured lifetime.
        """

        digest = getattr(auth_obj, "digest", None)

        if not digest:
            return

        try:
            token = SmarterAuthToken.objects.get(digest=digest)

        except SmarterAuthToken.DoesNotExist:

            logger.warning(
                "%s token digest not found",
                self.formatted_class_name,
            )

            return

        max_age = timedelta(days=smarter_settings.smarter_api_key_max_lifetime_days)

        if token.created < timezone.now() - max_age:

            logger.warning(
                ("%s token exceeded maximum lifetime " "user=%s " "max_days=%d"),
                self.formatted_class_name,
                user,
                smarter_settings.smarter_api_key_max_lifetime_days,
            )

    # pylint: disable=W0613
    def handle_authentication_failure(
        self,
        request: Request,
        token: str | None,
        exc: Exception,
    ):

        smarter_token_authentication_failure.send(
            sender=self.__class__,
            user=SmarterAnonymousUser(),
            token=token,
        )

        logger.warning("%s authentication failed token=%s", self.formatted_class_name, token)

        wrapped_exception = SmarterTokenAuthenticationError("Authentication failed.")

        thing = SAMKinds.from_url(self.smarter_build_absolute_uri(request))

        command = SmarterJournalCliCommands.from_url(self.smarter_build_absolute_uri(request))

        return SmarterJournaledJsonErrorResponse(
            request=request,
            e=wrapped_exception,
            thing=thing,
            command=command,  # type: ignore[arg-type]
            status=HTTPStatus.UNAUTHORIZED,
            stack_trace=traceback.format_exc(),
        )
