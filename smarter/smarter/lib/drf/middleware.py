"""
authenticate requests via SmarterTokenAuthentication, a subclass of
knox.auth TokenAuthentication tokens.
"""

import logging
from http import HTTPStatus

import waffle
from django.contrib.auth import login
from django.utils.deprecation import MiddlewareMixin
from knox.settings import knox_settings
from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.classes import SmarterHelperMixin
from smarter.common.const import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonErrorResponse

from .token_authentication import (
    SmarterTokenAuthentication,
    SmarterTokenAuthenticationError,
)


logger = logging.getLogger(__name__)

if waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING):
    logger.info("Loading smarter.lib.drf.middleware.SmarterTokenAuthenticationMiddleware")


class SmarterTokenAuthenticationMiddleware(MiddlewareMixin, SmarterHelperMixin):
    """
    authenticate requests via SmarterTokenAuthentication, a subclass of
    knox.auth TokenAuthentication tokens.
    """

    authorization_header = None
    request = None

    # pylint: disable=unused-argument
    def is_token_auth(self, request) -> bool:
        """Check if the request is for knox token authentication."""
        auth = self.authorization_header.split()
        prefix = knox_settings.AUTH_HEADER_PREFIX.encode()

        if not auth:
            return False
        if auth[0].lower() != prefix.lower():
            # Authorization header is possibly for another backend
            return False
        return True

    def url(self) -> str:
        """Return the full URL from the request object."""
        if self.request:
            return self.request.build_absolute_uri()

    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response

    def __call__(self, request):
        """Try to authenticate the request using SmarterTokenAuthentication."""
        self.authorization_header = get_authorization_header(request)
        self.request = request
        if not self.is_token_auth(request):
            # we're not using token authentication, no need to do anything
            return self.get_response(request)
        if hasattr(request, "auth"):
            # we've already authenticated the request
            # with some other middleware, no need to do anything
            return self.get_response(request)

        request.auth = SmarterTokenAuthentication()
        try:
            user, _ = request.auth.authenticate(request)
            if user:
                request.user = user
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            else:
                raise AuthenticationFailed(
                    "SmarterTokenAuthentication.authenticate() did not return"
                    " a user object. This can happen if the Authorization header"
                    " is malformed or is for another backend."
                )
            logger.info("%s authenticated user %s", self.formatted_class_name, user)
        except AuthenticationFailed as auth_failed:
            try:
                raise SmarterTokenAuthenticationError("Authentication failed.") from auth_failed
            except SmarterTokenAuthenticationError as e:
                auth = self.authorization_header.split()
                auth_token = auth[1] if len(auth) > 1 else None
                logger.warning(
                    "%s failed token authentication attempt using token %s", self.formatted_class_name, auth_token
                )
                thing = SAMKinds.from_url(self.url())
                command = SmarterJournalCliCommands.from_url(self.url())
                return SmarterJournaledJsonErrorResponse(
                    request=request, e=e, thing=thing, command=command, status=HTTPStatus.UNAUTHORIZED
                )

        return self.get_response(request)
