"""
Signing in with an email address and password, and signing up, for the console's sign-in pages and api.

The console's account api, :mod:`smarter.apps.account.api.web.views`, signs users in through these functions,
which record each failure in the login audit.
"""

from typing import Optional

from django.contrib.auth import authenticate, login
from django.http import HttpRequest

from smarter.apps.account.activation import (
    can_activate_by_email,
    send_activation_email,
)
from smarter.apps.account.login_audit import (
    LoginFailure,
    log_login_failure,
    login_identity,
    password_failure,
)
from smarter.apps.account.models import User
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING, SmarterWaffleSwitches.VIEW_LOGGING]
)
logger_prefix = logging.SmarterFormattedText.text(__name__)


def sign_in_with_email(request: HttpRequest, email: str, password: str) -> Optional[User]:
    """
    Sign in the user who has this email address and password, in the request's session.

    A failure is recorded in the login audit, with its reason: an unknown address, or the password
    failure of :func:`smarter.apps.account.login_audit.password_failure`. The caller answers every
    failure alike, so that the response doesn't reveal which addresses have accounts.

    :param request: The request, whose session the user is signed in to.
    :param email: The email address. An email address belongs to one user.
    :param password: The password.
    :returns: The signed-in user, or None.
    """
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        log_login_failure(email, LoginFailure.UNKNOWN_ACCOUNT)
        return None
    authenticated_user = authenticate(request, username=user.username, password=password)
    if authenticated_user is None:
        log_login_failure(email, password_failure(user))
        return None
    login(request, authenticated_user)
    logger.debug("%s.sign_in_with_email() signed in identity %s", logger_prefix, login_identity(email))
    return authenticated_user  # type: ignore[return-value]


def email_is_taken(email: str) -> bool:
    """
    Whether another user already has this email address, in any case.

    :param email: The email address.
    :returns: True when a user has it.
    """
    return User.objects.filter(email__iexact=email).exists()


def awaits_activation(email: str, password: str) -> bool:
    """
    Whether this email address and password are those of a user who hasn't activated their account yet.

    Only someone who knows the password is told, so the answer doesn't reveal which addresses have accounts.

    :param email: The email address.
    :param password: The password.
    :returns: True for an inactive user who may activate by email, and whose password this is.
    """
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        return False
    if not can_activate_by_email(user):
        return False
    return user.check_password(password)


def sign_up(request: HttpRequest, email: str, password: str) -> User:
    """
    Create an inactive user whose username and email address are ``email``, and email them an activation link.

    The user can sign in once they follow the link, which proves that the address is theirs. See
    :mod:`smarter.apps.account.activation`. The caller checks first that the address is free and that the
    password is acceptable.

    :param request: The request, for the link's host and the email's template context.
    :param email: The email address, which is also the username.
    :param password: The password.
    :returns: The new, inactive user.
    :raises RuntimeError: when the email's template can't be rendered.
    """
    user = User.objects.create_user(email, password=password, email=email, is_active=False)
    logger.info("%s.sign_up() created identity %s", logger_prefix, login_identity(email))
    send_activation_email(request, user)
    return user
