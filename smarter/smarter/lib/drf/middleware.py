"""
Middleware that authenticates api requests with a Smarter api key, using SmarterTokenAuthentication.

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
- :class:`SmarterTokenAuthenticationMiddleware`

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

from asgiref.sync import sync_to_async
from django.http import HttpResponseBase
from django.utils import timezone
from knox.settings import knox_settings
from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from smarter.apps.account.models import User
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import SmarterFormattedText
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
logger_prefix = SmarterFormattedText.text(__name__)

if waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_SMARTER_TOKEN_AUTH):
    logger.debug(
        "%s.SmarterTokenAuthenticationMiddleware is %s",
        logger_prefix,
        SmarterHelperMixin().formatted_state_ready,
    )
else:
    logger.debug(
        "%s.SmarterTokenAuthenticationMiddleware is %s. Enable with Django waffle in the admin console.",
        logger_prefix,
        SmarterHelperMixin().formatted_state_not_ready,
    )


class SmarterTokenAuthenticationMiddleware(SmarterMiddlewareMixin):
    """Middleware for token authentication using SmarterTokenAuthentication."""

    sync_capable = True
    async_capable = True

    @property
    def formatted_class_name(self) -> str:
        """The middleware's dotted class name, formatted for log messages."""
        class_name = f"{__name__}.{self.__class__.__name__}"
        return self.formatted_text(class_name)

    def __call__(self, request: Request) -> HttpResponseBase | Awaitable[HttpResponseBase]:
        """
        Handle a request: authenticate it in sync mode, or hand it to ``__acall__()`` in async mode.

        Requests for paths that deserve amnesty, e.g. health checks, skip
        authentication.

        :param request: The request.
        :returns: The response, or in async mode a coroutine that returns it.
        """
        if self.async_mode:
            return self.__acall__(request)

        if self.deserves_amnesty(request.path):
            return super().__call__(request)

        logger.debug("%s.__call__(): Request received: %s %s", self.formatted_class_name, request.method, request.path)

        return self.process_request(request)

    async def __acall__(self, request: Request) -> HttpResponseBase:
        """
        Handle a request in async mode, running ``process_request()`` in a thread.

        :param request: The request.
        :returns: The response.
        """
        logger.debug("%s.__acall__(): Request received: %s %s", self.formatted_class_name, request.method, request.path)
        # process_request() returns get_response()'s coroutine, in async mode, which must be awaited.
        response = await sync_to_async(self.process_request)(request)
        if inspect.isawaitable(response):
            response = await response
        return response

    def process_request(self, request: Request) -> HttpResponseBase | Awaitable[HttpResponseBase]:
        """
        Authenticate an api request that carries a token in its ``Authorization`` header.

        Non-api requests, requests that are already authenticated, and requests without a token
        pass through. A valid token's user becomes the request's user, for this request only, and
        the authentication request and success signals are sent. It does nothing unless the ``ENABLE_MIDDLEWARE_SMARTER_TOKEN_AUTH`` waffle
        switch is active.

        :param request: The request.
        :returns: The next handler's response (a coroutine in async mode), or a 401 journaled error
            response if the token fails.
        :raises ValueError: If the request's url can't be built.
        """
        if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_SMARTER_TOKEN_AUTH):
            return self.get_response(request)

        request = self.ensure_request_user(request)

        if getattr(request, "auth", None) is not None:
            logger.debug("%s.process_request() request already authenticated", self.formatted_class_name)
            return self.get_response(request)

        # The header is read first: it is the cheapest check, and most requests (console pages,
        # static files, chat) carry no token, so they skip building and classifying the url.
        authorization_header = self.get_authorization_header(request)

        token = self.extract_token(authorization_header)

        if not token:
            logger.debug("%s.process_request() no token authentication detected", self.formatted_class_name)
            return self.get_response(request)

        url = self.smarter_build_absolute_uri(request)
        if not isinstance(url, str):
            raise ValueError("Failed to build request URL.")

        logger.debug("%s.process_request() processing request: %s", self.formatted_class_name, url)

        if not self.is_api_request(url):
            logger.debug("%s.process_request() skipping non-api request", self.formatted_class_name)
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
            self.attach_user(request, user)

            smarter_token_authentication_success.send(
                sender=self.__class__,
                user=request.user,
                token=masked_token,
            )

            logger.debug("%s.process_request() authenticated user %s", self.formatted_class_name, request.user)

        except AuthenticationFailed as auth_failed:

            return self.handle_authentication_failure(
                request=request,
                token=masked_token,
                exc=auth_failed,
            )

        logger.debug("%s.process_request() authentication completed", self.formatted_class_name)

        return self.get_response(request)

    @staticmethod
    def is_api_request(url: str) -> bool:
        """
        Return whether a url is a Smarter api endpoint.

        :param url: The absolute url.
        :returns: True for an api endpoint.
        """
        return SmarterValidator.is_api_endpoint(url)

    @staticmethod
    def get_authorization_header(request: Request) -> str:
        """
        Return the request's ``Authorization`` header as a string.

        :param request: The request.
        :returns: The header, or an empty string.
        """
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
        """
        Return knox's ``AUTH_HEADER_PREFIX``, e.g. ``Token``, as a string.

        :returns: The prefix that an ``Authorization`` header's token must follow.
        """
        prefix = knox_settings.AUTH_HEADER_PREFIX

        if isinstance(prefix, bytes):
            return prefix.decode()

        return str(prefix)

    def extract_token(self, authorization_header: str) -> str | None:
        """
        Extract the token from an ``Authorization`` header of the form ``<prefix> <token>``.

        The prefix is compared with knox's ``AUTH_HEADER_PREFIX`` without regard to case.

        :param authorization_header: The header, or an empty string.
        :returns: The token, or None if the header is empty, malformed, or has another prefix.
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

        logger.debug(
            "%s.extract_token() detected token authentication token=%s",
            self.formatted_class_name,
            mask_string(token),
        )

        return token

    @staticmethod
    def ensure_request_user(request: Request) -> Request:
        """
        Set the request's user to an anonymous user when it has none.

        :param request: The request, which is changed in place.
        :returns: The same request.
        """
        if not hasattr(request, "user") or request.user is None:
            request.user = SmarterAnonymousUser()

        return request

    @staticmethod
    def attach_user(request, user: User) -> None:
        """
        Make a token's user the request's user, for this request only.

        It replaces ``django.contrib.auth.login()``, which an api request doesn't need: a token
        authenticates each request by itself. ``login()`` also wrote the user's ``last_login``,
        rotated the session and the CSRF token, and sent ``user_logged_in``, on every api request.

        Both ``request.user`` and the async ``request.auser()`` return the user, as they would
        after a login, e.g. for the logging context middleware.

        :param request: The request.
        :param user: The token's user.
        """
        request.user = user
        request._cached_user = user  # pylint: disable=protected-access

        async def auser() -> User:
            return user

        request.auser = auser

    @staticmethod
    def authenticate_request(request: Request) -> tuple[User, SmarterAuthToken]:
        """
        Authenticate the request's token with :class:`SmarterTokenAuthentication`, and set ``request.auth``.

        :param request: The request.
        :returns: A tuple of the user and the token.
        :raises AuthenticationFailed: If the token is invalid or has no user.
        """
        logger.debug(
            "%s.SmarterTokenAuthenticationMiddleware.authenticate_request() called",
            logger_prefix,
        )

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
        user: User,
        auth_obj: SmarterAuthToken,
    ) -> None:
        """
        Log a warning when a token is older than ``smarter_api_key_max_lifetime_days``.

        The token is not rejected; only a warning is logged.

        :param user: The authenticated user, for the log message.
        :param auth_obj: The authenticated token. Any other object with a ``digest`` is looked up
            by its digest.
        """
        digest = getattr(auth_obj, "digest", None)

        if not digest:
            return

        # authenticate_credentials() returns the SmarterAuthToken itself, so there is no need to fetch it again.
        token = auth_obj if isinstance(auth_obj, SmarterAuthToken) else None
        if token is None:
            try:
                token = SmarterAuthToken.objects.get(digest=digest)

            except SmarterAuthToken.DoesNotExist:

                logger.warning(
                    "%s.validate_token_lifetime() token digest not found",
                    self.formatted_class_name,
                )

                return

        max_age = timedelta(days=smarter_settings.smarter_api_key_max_lifetime_days)

        if token.created < timezone.now() - max_age:

            logger.warning(
                "%s.validate_token_lifetime() token exceeded maximum lifetime user=%s max_days=%d",
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
    ) -> SmarterJournaledJsonErrorResponse:
        """
        Send the authentication failure signal, and return a 401 journaled error response.

        :param request: The request.
        :param token: The masked token.
        :param exc: The authentication error.
        :returns: The 401 :class:`SmarterJournaledJsonErrorResponse`.
        """
        smarter_token_authentication_failure.send(
            sender=self.__class__,
            user=SmarterAnonymousUser(),
            token=token,
            error=exc,
        )

        logger.warning(
            "%s.handle_authentication_failure() authentication failed token=%s",
            self.formatted_class_name,
            token,
        )

        wrapped_exception = SmarterTokenAuthenticationError("Authentication failed.")

        url = self.smarter_build_absolute_uri(request)

        # from_url() raises TypeError on None, so a request without a url has no thing or command.
        thing = None
        command = None
        if url is not None:
            thing = SAMKinds.from_url(url)
            command = SmarterJournalCliCommands.from_url(url)

        return SmarterJournaledJsonErrorResponse(
            request=request,
            e=wrapped_exception,
            thing=thing,
            command=command,  # type: ignore[arg-type]
            status=HTTPStatus.UNAUTHORIZED,
            stack_trace=traceback.format_exc(),
        )
