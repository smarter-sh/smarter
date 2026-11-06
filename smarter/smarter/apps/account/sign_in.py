"""
Signing in with an email address and password, and signing up, for the console's sign-in pages and api.

The server-rendered sign-in and sign-up pages, :class:`~smarter.apps.account.views.authentication.LoginView`
and :class:`~smarter.apps.account.views.authentication.AccountRegisterView`, and the console's account api,
:mod:`smarter.apps.account.api.web.views`, all sign users in through these functions, so that each failure
is audited in the same way and the answers are the same.
"""

from typing import Optional

from django.contrib.auth import authenticate, login
from django.http import HttpRequest

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


def sign_up(request: HttpRequest, email: str, password: str) -> User:
    """
    Create a user whose username and email address are ``email``, and sign them in.

    The caller checks first that the address is free and that the password is acceptable.

    :param request: The request, whose session the new user is signed in to.
    :param email: The email address, which is also the username.
    :param password: The password.
    :returns: The new, signed-in user.
    :raises RuntimeError: when the new user can't be authenticated, which is a bug.
    """
    User.objects.create_user(email, password=password, email=email)
    authenticated_user = authenticate(request, username=email, password=password)
    if authenticated_user is None:
        raise RuntimeError(f"{logger_prefix}.sign_up() authentication failed immediately after registration.")
    login(request, authenticated_user)
    logger.info("%s.sign_up() created and signed in identity %s", logger_prefix, login_identity(email))
    return authenticated_user  # type: ignore[return-value]
