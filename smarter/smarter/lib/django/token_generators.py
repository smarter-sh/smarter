"""Django token generators for single-use authentications."""

from typing import Union
from urllib.parse import urlparse

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpRequest
from django.utils.encoding import force_bytes
from django.utils.http import (
    base36_to_int,
    urlsafe_base64_decode,
    urlsafe_base64_encode,
)
from rest_framework.request import Request

from smarter.apps.account.models import User
from smarter.common.exceptions import SmarterException
from smarter.lib.django.shortcuts import reverse

DEFAULT_LINK_EXPIRATION = 86400
"""How many seconds a link stays valid, unless the generator is given another expiration: one day."""

SmarterRequest = Union[HttpRequest, Request]
"""A Django or a DRF request, either of which :meth:`ExpiringTokenGenerator.encode_link` accepts."""


class SmarterTokenError(SmarterException):
    """Base class for all token-related exceptions."""


class SmarterTokenParseError(SmarterTokenError):
    """Raised when a token is not two parts separated by one dash."""


class SmarterTokenConversionError(SmarterTokenError):
    """Raised when a token's timestamp part is not a valid base36 number."""


class SmarterTokenExpiredError(SmarterTokenError):
    """Raised when a token is older than its generator's expiration."""


class SmarterTokenIntegrityError(SmarterTokenError):
    """Raised when a token fails Django's token check for the user."""


class ExpiringTokenGenerator(PasswordResetTokenGenerator):
    """An object of this class can generate a token that expires after a certain amount of time."""

    def __init__(self, expiration: int = DEFAULT_LINK_EXPIRATION):
        """
        Initialize the generator.

        :param expiration: How many seconds a token stays valid.
        """
        self.expiration = expiration
        super().__init__()

    def user_to_uidb64(self, user: User) -> str:
        """
        Encode a user's primary key as url-safe base64.

        :param user: The user.
        :returns: The encoded primary key.
        """
        return urlsafe_base64_encode(force_bytes(user.pk))

    def uidb64_to_user(self, uidb64: str) -> User:
        """
        Fetch the user whose primary key is encoded in ``uidb64``.

        :param uidb64: The url-safe base64 encoded primary key.
        :returns: The user.
        :raises User.DoesNotExist: If there is no such user.
        """
        uid = urlsafe_base64_decode(uidb64).decode()
        return User.objects.get(pk=uid)

    def encode_link(self, request: SmarterRequest, user: User, reverse_link: str) -> str:
        """
        Create an encoded url link that expires after a certain amount of time.

        The protocol comes from the ``X-Forwarded-Proto`` header, else from the request, and
        defaults to https if neither can be read.

        :param request: The request, which gives the current site's domain and the protocol.
        :param user: The user the link is for.
        :param reverse_link: The url name to reverse, with ``uidb64`` and ``token`` kwargs.
        :returns: The absolute url.
        """
        token = self.make_token(user=user)
        domain = get_current_site(request).domain
        uid = self.user_to_uidb64(user)
        slug = reverse(reverse_link, kwargs={"uidb64": uid, "token": token})

        # try to determine the protocol (http or https) from the originating
        # request. default to https if it cannot be determined
        try:
            proto_header = request.META.get("HTTP_X_FORWARDED_PROTO")
            if proto_header:
                protocol = proto_header.split(",")[0].strip()
            elif hasattr(request, "is_secure") and request.is_secure():
                protocol = "https"
            else:
                protocol = "http"
        # pylint: disable=broad-except
        except Exception:
            protocol = "https"

        url = protocol + "://" + domain + slug
        return url

    def decode_link(self, uidb64: str, token: str) -> User:
        """
        Extract the user from the uid and token and validate.

        :param uidb64: The url-safe base64 encoded primary key of the user.
        :param token: The token.
        :returns: The user.
        :raises SmarterTokenError: If the token is malformed, invalid or expired.
        """
        user = self.uidb64_to_user(uidb64)
        self.validate(user, token)
        return user

    def parse_link(self, url: str) -> tuple[User, str]:
        """
        Return the user and token from a link made by :meth:`encode_link`, without validating the token.

        The last two path segments are the encoded user id and the token.

        :param url: The link.
        :returns: A tuple of the user and the token.
        :raises User.DoesNotExist: If there is no such user.
        """
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip("/").split("/")
        uidb64 = path_parts[-2]
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
        token = path_parts[-1]
        return user, token

    def get_timestamp(self) -> int:
        """
        Return the current time on the clock that Django's tokens use.

        Django stamps a token with the seconds since 2001-01-01, so a token's age is
        this value minus the token's own timestamp.

        :returns: The seconds since 2001-01-01.
        """
        now = self._now()
        return self._num_seconds(now)

    def token_age(self, timestamp: int) -> int:
        """
        Return how many seconds ago a token was made.

        :param timestamp: The token's timestamp, the base36-decoded first part of the token.
        :returns: The token's age, in seconds.
        """
        current_time = self.get_timestamp()
        age = current_time - timestamp
        return age

    def validate(self, user: User, token: str) -> bool:
        """
        Check that a password reset token is correct for a given user.

        :param user: The user.
        :param token: The token.
        :returns: True if the token is valid.
        :raises SmarterTokenParseError: If the token is not two parts separated by a dash.
        :raises SmarterTokenIntegrityError: If the token fails Django's check.
        :raises SmarterTokenConversionError: If the timestamp part is not base36.
        :raises SmarterTokenExpiredError: If the token is older than ``expiration`` seconds.
        """
        # Ensure token contains exactly one dash and two parts
        parts = token.split("-")
        if len(parts) != 2:
            raise SmarterTokenParseError("Token is not properly formed. It should contain one dash and two parts.")

        if not self.check_token(user, token):
            raise SmarterTokenIntegrityError("Token is invalid.")

        timestamp_b36 = parts[0]

        try:
            timestamp = base36_to_int(timestamp_b36)
        except ValueError as exc:
            raise SmarterTokenConversionError("Token is invalid.") from exc

        age = self.token_age(timestamp)
        if age > self.expiration:
            raise SmarterTokenExpiredError("Token has expired.")

        return True
