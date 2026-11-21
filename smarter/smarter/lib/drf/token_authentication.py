"""Knox TokenAuthentication subclass that checks if the token is active."""

from hmac import compare_digest
from typing import Optional, Union

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from django.utils import timezone
from knox import crypto
from knox.auth import TokenAuthentication
from knox.settings import CONSTANTS
from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from smarter.apps.account.models import User
from smarter.common.exceptions import SmarterException
from smarter.common.mixins import SmarterHelperMixin
from smarter.common.utils import mask_string
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .models import SmarterAuthToken
from .signals import (
    smarter_token_authentication_failure,
    smarter_token_authentication_request,
    smarter_token_authentication_success,
)


# pylint: disable=W0613
def should_log(level: int) -> bool:
    """
    Return whether this module logs, which it does while the ``API_LOGGING`` waffle switch is active.

    :param level: The log level, which is ignored.
    :returns: True if the switch is active.
    """
    return waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING)


RequestType = Union[HttpRequest, Request]
"""A Django request, or DRF's wrapper of one."""

AUTHENTICATED_TOKEN_ATTRIBUTE = "_smarter_authenticated_token"
"""
The Django request's attribute that keeps its token's authentication: the token, its user and its api key.

See :meth:`SmarterTokenAuthentication.remembered`.
"""

base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SmarterTokenAuthenticationError(SmarterException):
    """Base class for all SmarterTokenAuthentication errors."""

    @property
    def get_formatted_err_message(self):
        """The error message prefix of token authentication errors."""
        return "Smarter Token Authentication error"


# pylint: disable=W0223
class SmarterAnonymousUser(AnonymousUser):
    """AnonymousUser subclass for SmarterTokenAuthenticationMiddleware logging purposes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.smarter = f"{__name__}.{SmarterAnonymousUser.__name__}"


class SmarterTokenAuthentication(TokenAuthentication, SmarterHelperMixin):
    """
    Django REST Framework (DRF) knox TokenAuthentication that also checks that the token is active.

    This subclass adds:

    - a check of the token's ``is_active`` field, so that tokens can be disabled
    - Django signals for token authentication events
    - logging
    - an update of the token's ``last_used_at`` when it is used

    Authentication raises :class:`~rest_framework.exceptions.AuthenticationFailed` for any failure
    to authenticate the request's token.
    """

    model = SmarterAuthToken

    @property
    def formatted_class_name(self) -> str:
        """Return the formatted class name for logging purposes."""
        class_name = f"{__name__}.{SmarterTokenAuthentication.__name__}"
        return self.formatted_text(class_name)

    def __init__(self, *args, **kwargs):
        """
        Initialize the authentication backend.

        :param args: Passed to knox's ``TokenAuthentication``.
        :param kwargs: Passed to knox's ``TokenAuthentication``.
        """
        super().__init__(*args, **kwargs)
        logger.debug(
            "called args: %s, kwargs: %s",
            args,
            kwargs,
        )

    @staticmethod
    def remembered(request: Optional[RequestType], token: bytes) -> Optional[tuple[User, SmarterAuthToken]]:
        """
        Return the user and api key that ``token`` was already authenticated as for this request.

        Several layers authenticate the same request's token: the token middleware, the CSRF
        middleware's request classification, :class:`~smarter.apps.account.mixins.AccountMixin` and
        DRF's own authentication classes. The first success is kept on the Django request, so that
        the others don't repeat the database lookups and writes. It lives only as long as the request.

        :param request: The request, a Django request or DRF's wrapper of one, or None.
        :param token: The token from the request's ``Authorization`` header.
        :returns: The user and api key, or None if this token wasn't authenticated for this request.
        """
        if request is None:
            return None
        django_request = getattr(request, "_request", request)
        authenticated = getattr(django_request, AUTHENTICATED_TOKEN_ATTRIBUTE, None)
        if authenticated is None:
            return None
        authenticated_token, user, smarter_auth_token = authenticated
        if not compare_digest(authenticated_token, token):
            return None
        return user, smarter_auth_token

    @staticmethod
    def remember(
        request: Optional[RequestType], token: bytes, user: User, smarter_auth_token: SmarterAuthToken
    ) -> None:
        """
        Keep a successful authentication on the Django request, for :meth:`remembered`.

        :param request: The request, a Django request or DRF's wrapper of one, or None.
        :param token: The token from the request's ``Authorization`` header.
        :param user: The token's user.
        :param smarter_auth_token: The token's api key.
        """
        if request is None:
            return
        django_request = getattr(request, "_request", request)
        authenticated = (token, user, smarter_auth_token)
        setattr(django_request, AUTHENTICATED_TOKEN_ATTRIBUTE, authenticated)

    @classmethod
    def authenticate_for_request(cls, request: Optional[RequestType], token: bytes) -> tuple[User, SmarterAuthToken]:
        """
        Authenticate a token that a request carries, once per request.

        :param request: The request that carries the token, or None if there is none.
        :param token: The token from the request's ``Authorization`` header.
        :returns: A tuple of the authenticated user and their :class:`SmarterAuthToken`.
        :raises AuthenticationFailed: As :meth:`authenticate_credentials` does.
        """
        remembered = cls.remembered(request, token)
        if remembered is not None:
            return remembered
        user, smarter_auth_token = cls().authenticate_credentials(token)
        cls.remember(request, token, user, smarter_auth_token)
        return user, smarter_auth_token

    def authenticate(self, request: Request) -> Optional[tuple[User, SmarterAuthToken]]:
        """
        Authenticate a request's ``Authorization: Token ...`` header, as knox does, once per request.

        A token that was already authenticated for this request (see :meth:`remembered`) is not
        authenticated again.

        :param request: The request.
        :returns: The user and api key, or None if the request has no token header.
        :raises AuthenticationFailed: If the header is malformed, or the token fails.
        """
        header_parts = get_authorization_header(request).split()
        token = None
        if len(header_parts) == 2:
            token = header_parts[1]
        if token is not None:
            remembered = self.remembered(request, token)
            if remembered is not None:
                return remembered

        user_auth_tuple = super().authenticate(request)
        if user_auth_tuple is None:
            return None
        if token is not None:
            user, smarter_auth_token = user_auth_tuple
            self.remember(request, token, user, smarter_auth_token)
        return user_auth_tuple

    def authenticate_credentials(self, token: bytes) -> tuple[User, SmarterAuthToken]:
        """
        Authenticate a token as knox does, then check that the token is active.

        Sends the token authentication request signal, and the success or failure signal. On
        success, it updates the token's ``last_used_at`` at most once per
        ``SmarterAuthToken.LAST_USED_RESOLUTION``, with a queryset update.

        :param token: The token from the request's ``Authorization`` header.
        :returns: A tuple of the authenticated user and their :class:`SmarterAuthToken`.
        :raises AuthenticationFailed: If the token is not bytes, if knox can't authenticate it, or
            if the token is not active.
        """
        logger.debug("called with token: %s", mask_string(token))
        if not isinstance(token, bytes):
            logger.warning(
                "invalid token type: %s. Expected bytes.",
                type(token),
            )
            raise AuthenticationFailed("Invalid token type. Expected bytes")
        masked_token = mask_string(string=token.decode())
        smarter_token_authentication_request.send(sender=self.__class__, token=masked_token, url=None)
        logger.debug("%s", masked_token)
        try:
            user, auth_token = super().authenticate_credentials(token)
            logger.debug(
                "retrieved user %s of type %s for token: %s",
                user,
                type(user),
                masked_token,
            )
        except AuthenticationFailed as e:
            smarter_token_authentication_failure.send(
                sender=self.__class__, user=SmarterAnonymousUser(), token=masked_token, error=e
            )
            raise

        # next, we need to ensure that the token is active, otherwise
        # we should raise an exception that exactly matches the one
        # raised by the default token authentication
        # By primary key: knox's digest, which is unique, unlike token_key, an 8-character prefix.
        smarter_auth_token = SmarterAuthToken.objects.get(pk=auth_token.pk)
        if not smarter_auth_token.is_active:
            error = AuthenticationFailed("Api key is not activated.")
            smarter_token_authentication_failure.send(
                sender=self.__class__,
                user=user,
                token=masked_token,
                error=error,
            )
            logger.warning(
                "token is not active for user %s, token: %s",
                user,
                masked_token,
            )
            raise error

        # update the last used time for the token, at most once per LAST_USED_RESOLUTION, since
        # every request is authenticated. A queryset update, rather than save(), so that
        # authenticating a request doesn't invalidate and reload the token's cached objects.
        now = timezone.now()
        if smarter_auth_token.last_used_is_stale(now):
            smarter_auth_token.last_used_at = now
            SmarterAuthToken.objects.filter(pk=smarter_auth_token.pk).update(last_used_at=now)

        # if the token is active, we can return the user and token as a tuple
        # exactly as the default token authentication does.
        smarter_token_authentication_success.send(
            sender=self.__class__,
            user=user,
            token=masked_token,
        )
        logger.info("authenticated user %s", user)
        return (user, smarter_auth_token)

    @classmethod
    def get_user_from_request(cls, request: Request) -> User | SmarterAnonymousUser:
        """
        Return the user of the active token in a request's ``Authorization: Token ...`` header.

        Unlike :meth:`authenticate_credentials`, this sends no signals, and doesn't update the
        token's ``last_used_at``.

        :param request: The request.
        :returns: The token's user if the token is valid and active, otherwise a
            :class:`SmarterAnonymousUser`.
        """
        logger.debug("called with request: %s", request)

        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if not auth_header or not auth_header.startswith("Token "):
            logger.warning(
                "no valid Token authorization header found. Returning SmarterAnonymousUser.",
            )
            return SmarterAnonymousUser()
        token = auth_header.split("Token ")[1].strip()
        # As knox does: token_key holds only the token's first characters, so the
        # token is looked up by them, and verified by comparing its hash with the digest.
        digest = crypto.hash_token(token)
        for auth_token in SmarterAuthToken.objects.filter(token_key=token[: CONSTANTS.TOKEN_KEY_LENGTH]):
            if compare_digest(digest, auth_token.digest) and auth_token.is_active:
                # never log token_key: it is the first characters of the token itself.
                logger.debug(
                    "retrieved user %s for token: %s",
                    auth_token.user,
                    auth_token.identifier,
                )
                return auth_token.user
        logger.warning(
            "failed to retrieve an active token for token: %s. Returning SmarterAnonymousUser.",
            mask_string(token),
        )
        return SmarterAnonymousUser()
