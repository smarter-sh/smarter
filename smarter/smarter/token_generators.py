# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring
"""Django token generators for single-use authentications."""
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import base36_to_int
from django.utils.timezone import now as timezone_now


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

    @staticmethod
    def get_timestamp() -> int:
        return int(timezone_now().timestamp())

    def adjusted_timestamp(self, timestamp: int) -> int:
        return timestamp + HFS_EPOCH_UNIX_TIMESTAMP

    def validate(self, user, token, expiration=86400) -> bool:
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

        if (current_time - adjusted_timestamp) > expiration:
            raise TokenExpiredError("Token has expired.")

        return True
