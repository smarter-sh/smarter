"""
authenticate requests via SmarterTokenAuthentication, a subclass of
knox.auth TokenAuthentication tokens.
"""

import logging
import traceback
from http import HTTPStatus

from django.contrib.auth import login
from django.utils.deprecation import MiddlewareMixin
from knox.settings import knox_settings
from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.classes import SmarterHelperMixin
from smarter.common.const import SmarterWaffleSwitches
from smarter.common.utils import mask_string
from smarter.lib.django import waffle
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonErrorResponse

from .signals import (
    smarter_token_authentication_failure,
    smarter_token_authentication_request,
    smarter_token_authentication_success,
)
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
    masked_token: str = None

    # pylint: disable=unused-argument
    def is_token_auth(self, request) -> bool:
        """Check if the request is for knox token authentication."""
        # auth=[b'Token', b'd9d56ff4-- A 64-CHARACTER TOKEN --c8176']
        auth = self.authorization_header.split()
        auth = [a.decode() if isinstance(a, bytes) else a for a in auth]
        prefix = str(knox_settings.AUTH_HEADER_PREFIX)

        if not auth:
            return False

        # Ensure auth[0] is a string for comparison
        # prefix=Token
        # auth=['Token', 'd9d56ff4-- A 64-CHARACTER TOKEN --c8176']
        auth_prefix = auth[0]
        if auth_prefix.lower() != prefix.lower():
            # Authorization header is possibly for another backend
            return False

        token = auth[1]
        self.masked_token = mask_string(string=token)
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
        if getattr(request, "auth", None) is not None:
            # we've already authenticated the request
            # with some other middleware, no need to do anything
            return self.get_response(request)

        smarter_token_authentication_request.send(
            sender=self.__class__,
            token=self.masked_token,
        )
        request.auth = SmarterTokenAuthentication()
        try:
            user, _ = request.auth.authenticate(request)
            if user:
                request.user = user
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                smarter_token_authentication_success.send(
                    sender=self.__class__,
                    user=user,
                    token="i'm from middleware",
                )
            else:
                raise AuthenticationFailed(
                    "SmarterTokenAuthentication.authenticate() did not return"
                    " a user object. This can happen if the Authorization header"
                    " is malformed or is for another backend."
                )
            logger.info("%s authenticated user %s", self.formatted_class_name, user)
        except AuthenticationFailed as auth_failed:
            smarter_token_authentication_failure.send(
                sender=self.__class__,
                user=None,
                token="i'm from middleware",
            )
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
                    request=request,
                    e=e,
                    thing=thing,
                    command=command,
                    status=HTTPStatus.UNAUTHORIZED,
                    stack_trace=traceback.format_exc(),
                )

        return self.get_response(request)
