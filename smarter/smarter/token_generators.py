# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring
"""Django token generators for single-use authentications."""
from urllib.parse import urlparse

from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import (
    base36_to_int,
    urlsafe_base64_decode,
    urlsafe_base64_encode,
)
from django.utils.timezone import now as timezone_now


DEFAULT_LINK_EXPIRATION = 86400
HFS_EPOCH_UNIX_TIMESTAMP = 2082844800


class TokenParseError(Exception):
    pass


class TokenConversionError(Exception):
    pass


class TokenExpiredError(Exception):
    pass


class TokenIntegrityError(Exception):
    pass


class ExpiringTokenGenerator(PasswordResetTokenGenerator):
    """
    An object of this class can generate a token that expires after a certain amount of time.
    """

    def __init__(self, expiration: int = DEFAULT_LINK_EXPIRATION):
        self.expiration = expiration
        super().__init__()

    def user_to_uidb64(self, user: User) -> str:
        return urlsafe_base64_encode(force_bytes(user.pk))

    def uidb64_to_user(self, uidb64: str) -> User:
        uid = urlsafe_base64_decode(uidb64)
        return User.objects.get(pk=uid)

    def encode_link(self, request, user, reverse_link) -> str:
        """Create an encoded url link that expires after a certain amount of time."""
        token = self.make_token(user=user)
        domain = get_current_site(request).domain
        uid = self.user_to_uidb64(user)
        slug = reverse(reverse_link, kwargs={"uidb64": uid, "token": token})
        protocol = "https" if request.is_secure() else "http"
        url = protocol + "://" + domain + slug
        return url

    def decode_link(self, uidb64, token) -> User:
        """Extract the user from the uid and token and validate."""
        user = self.uidb64_to_user(uidb64)
        self.validate(user, token)
        return user

    def parse_link(self, url: str):
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip("/").split("/")
        uidb64 = path_parts[-2]
        uid = urlsafe_base64_decode(uidb64)
        user = User.objects.get(pk=uid)
        token = path_parts[-1]
        return user, token

    @staticmethod
    def get_timestamp() -> int:
        return int(timezone_now().timestamp())

    def adjusted_timestamp(self, timestamp: int) -> int:
        return timestamp + HFS_EPOCH_UNIX_TIMESTAMP

    def validate(self, user, token) -> bool:
        """
        Check that a password reset token is correct for a given user.
        """
        if not self.check_token(user, token):
            raise TokenIntegrityError("Token is invalid.")

        try:
            timestamp_b36 = token.split("-")[0]
        except ValueError as exc:
            raise TokenParseError("Token is not properly formed.") from exc

        try:
            timestamp = base36_to_int(timestamp_b36)
        except ValueError as exc:
            raise TokenConversionError("Token is invalid.") from exc

        adjusted_timestamp = self.adjusted_timestamp(timestamp)
        current_time = self.get_timestamp()

        if (current_time - adjusted_timestamp) > self.expiration:
            raise TokenExpiredError("Token has expired.")

        return True
