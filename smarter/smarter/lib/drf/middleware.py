"""
authenticate requests via SmarterTokenAuthentication, a subclass of
knox.auth TokenAuthentication tokens.
"""

import logging
from http import HTTPStatus

from django.contrib.auth import login
from django.utils.deprecation import MiddlewareMixin
from knox.settings import knox_settings
from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from smarter.lib.journal.http import SmarterJournaledJsonErrorResponse

from .token_authentication import (
    SmarterTokenAuthentication,
    SmarterTokenAuthenticationError,
)


logger = logging.getLogger(__name__)


class SmarterTokenAuthenticationMiddleware(MiddlewareMixin):
    """
    authenticate requests via SmarterTokenAuthentication, a subclass of
    knox.auth TokenAuthentication tokens.
    """

    authorization_header = None

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

    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response

    def __call__(self, request):
        """Try to authenticate the request using SmarterTokenAuthentication."""
        self.authorization_header = get_authorization_header(request)
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
            login(request, user)
            logger.info("%s() authenticated user %s", self.__class__.__name__, user)
        except AuthenticationFailed as auth_failed:
            try:
                raise SmarterTokenAuthenticationError("Authentication failed.") from auth_failed
            except SmarterTokenAuthenticationError as e:
                auth = self.authorization_header.split()
                auth_token = auth[1] if len(auth) > 1 else None
                logger.warning(
                    "%s() failed token authentication attempt using token %s", self.__class__.__name__, auth_token
                )
                return SmarterJournaledJsonErrorResponse(request=request, e=e, status=HTTPStatus.UNAUTHORIZED)

        return self.get_response(request)
