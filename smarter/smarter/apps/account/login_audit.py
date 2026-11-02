"""
The audit log of failed sign-ins to the web console.

Each failed sign-in is logged once, at WARNING, so that it is emitted whether or not the
account app's logging switch is on. The line names why the sign-in failed, as a
:class:`LoginFailure`, and who tried, as :func:`login_identity`: a keyed hash of the email
address, not the address itself. People sometimes type their password into the email
field, and the platform's logs are kept and searched, so the text that someone typed is
never logged.

Whoever helps a user with a sign-in problem computes the same hash from the user's verified
email address, and searches the logs for it:

.. code-block:: python

    from smarter.apps.account.login_audit import login_identity

    login_identity("user@example.com")  # e.g. 'a3f09c41d27e5b18'

The hash is keyed with the platform's ``SECRET_KEY``, so it cannot be reversed with a list of
known email addresses without that key, and differs between platforms.
"""

from enum import StrEnum
from typing import Optional

from django.utils.crypto import salted_hmac

from smarter.apps.account.models import User
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

LOGIN_IDENTITY_SALT = "smarter.apps.account.login_audit.login_identity"
"""The salt of :func:`login_identity`'s hash.

Changing it changes every identity.
"""

LOGIN_IDENTITY_LENGTH = 16
"""The number of hexadecimal characters of :func:`login_identity`."""


class LoginFailure(StrEnum):
    """Why a sign-in failed."""

    INVALID_FORM = "invalid_form"
    """The form was incomplete, or its email address was not valid."""

    UNKNOWN_ACCOUNT = "unknown_account"
    """No user has the email address."""

    INACTIVE_ACCOUNT = "inactive_account"
    """The user exists but is not active."""

    NO_PASSWORD = "no_password"
    """The user has no password, e.g. because they signed up with Google or GitHub."""

    WRONG_PASSWORD = "wrong_password"
    """The user is active and has a password, and the password did not match."""

    ERROR = "error"
    """The sign-in raised an exception."""


def login_identity(email: Optional[str]) -> str:
    """
    Return the identity of an email address in the audit log: a keyed hash of it.

    The address is stripped and lower cased first, so that the same address typed
    differently has the same identity.

    :param email: The email address, as typed or as stored.
    :returns: :data:`LOGIN_IDENTITY_LENGTH` hexadecimal characters, or ``"none"`` if there is no address.
    """
    normalized = (email or "").strip().lower()
    if not normalized:
        return "none"
    return salted_hmac(LOGIN_IDENTITY_SALT, normalized, algorithm="sha256").hexdigest()[:LOGIN_IDENTITY_LENGTH]


def password_failure(user: User) -> LoginFailure:
    """
    Return why an existing user's password was not accepted.

    Django's ``ModelBackend`` rejects an inactive user, and a user without a usable password,
    as it rejects a wrong password, so the user's own state tells them apart.

    :param user: The user whose sign-in failed.
    :returns: The reason.
    """
    if not user.is_active:
        return LoginFailure.INACTIVE_ACCOUNT
    if not user.has_usable_password():
        return LoginFailure.NO_PASSWORD
    return LoginFailure.WRONG_PASSWORD


def log_login_failure(email: Optional[str], failure: LoginFailure) -> None:
    """
    Log a failed sign-in.

    :param email: The email address that was typed, which is logged only as its :func:`login_identity`.
    :param failure: Why the sign-in failed.
    """
    logger.warning(
        "%s.log_login_failure() sign-in failed: reason=%s identity=%s",
        logger_prefix,
        failure,
        login_identity(email),
    )


__all__ = [
    "LOGIN_IDENTITY_LENGTH",
    "LOGIN_IDENTITY_SALT",
    "LoginFailure",
    "log_login_failure",
    "login_identity",
    "password_failure",
]
