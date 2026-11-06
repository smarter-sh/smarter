"""
The console's account api, ``/api/web/account/``: signing in and out, signing up and activating an account,.

and resetting a password.

These replace what the server-rendered sign-in pages' forms did, as JSON for the single-page console
(ADR-035). Every POST needs the CSRF token, which ``GET /api/web/session/`` sets. Signing in, signing up and
asking for an activation or password reset link are limited per IP address by
:class:`~smarter.lib.drf.throttling.SmarterCredentialsRateThrottle`. The bodies and responses are the models
of :mod:`smarter.apps.account.api.web.contract`.

These endpoints are part of Smarter's Django-React integration. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from http import HTTPStatus
from typing import Optional, TypeVar

from django.contrib.auth import logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from pydantic import ValidationError

from smarter.apps.account.activation import activate, resend_activation_email
from smarter.apps.account.api.web.contract import (
    AccountErrors,
    AccountMessage,
    ActivationResendRequest,
    NewPasswordRequest,
    PasswordResetRequest,
    SignInRequest,
    SignUpRequest,
)
from smarter.apps.account.email_links import EmailLinkError
from smarter.apps.account.models import User
from smarter.apps.account.password_reset import (
    send_password_reset_email,
    user_from_reset_link,
)
from smarter.apps.account.sign_in import (
    awaits_activation,
    email_is_taken,
    sign_in_with_email,
    sign_up,
)
from smarter.apps.api.web.session.contract import ConsoleSessionModel
from smarter.apps.api.web.session.views import console_session
from smarter.lib import json, logging
from smarter.lib.django import waffle
from smarter.lib.django.views import SmarterView
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.throttling import credentials_throttle_wait

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING, SmarterWaffleSwitches.VIEW_LOGGING]
)
logger_prefix = logging.SmarterFormattedText.text(__name__)

RequestModel = TypeVar("RequestModel", bound=ConsoleSessionModel)


class InvalidRequest(Exception):
    """A request whose body isn't the JSON that its endpoint takes."""


def errors_response(
    detail: str,
    field_errors: Optional[dict[str, list[str]]] = None,
    status: HTTPStatus = HTTPStatus.BAD_REQUEST,
) -> JsonResponse:
    """
    The response to a refused request.

    :param detail: Why, for the whole form.
    :param field_errors: The messages of each refused field, by its camelCase name.
    :param status: The http status.
    :returns: An :class:`~smarter.apps.account.api.web.contract.AccountErrors`, as JSON.
    """
    errors = AccountErrors(detail=detail, field_errors=field_errors or {})
    return JsonResponse(errors.to_json(), status=status)


def message_response(detail: str) -> JsonResponse:
    """
    The response to a request that succeeded, with a message for the user.

    :param detail: What happened.
    :returns: An :class:`~smarter.apps.account.api.web.contract.AccountMessage`, as JSON.
    """
    return JsonResponse(AccountMessage(detail=detail).to_json(), status=HTTPStatus.OK)


def session_response(request: HttpRequest) -> JsonResponse:
    """
    The console's session after signing in, out or up.

    :param request: The request, whose session changed.
    :returns: The new :class:`~smarter.apps.api.web.session.contract.ConsoleSession`, as JSON.
    """
    return JsonResponse(console_session(request).to_json(), status=HTTPStatus.OK)


def unknown_error_response() -> JsonResponse:
    """
    The response to a request that failed on the server, e.g. an email that couldn't be rendered.

    :returns: 500, with a message for the user.
    """
    return errors_response(
        _("An unknown error occurred. Please try again later."),
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
    )


def link_error_response(error: EmailLinkError) -> JsonResponse:
    """
    The response to an emailed link that can't be used.

    :param error: Why.
    :returns: 404, 403 or 400, with the reason.
    """
    return errors_response(str(error), status=error.status)


def throttled_response(wait: int) -> JsonResponse:
    """
    The response to a request over the credentials rate limit.

    :param wait: The seconds to wait before retrying.
    :returns: A 429 response, with a ``Retry-After`` header.
    """
    response = errors_response(
        _("Too many attempts. Try again in a minute."),
        status=HTTPStatus.TOO_MANY_REQUESTS,
    )
    response["Retry-After"] = str(wait)
    return response


def email_errors(email: str) -> list[str]:
    """
    The messages of an email address that isn't valid.

    :param email: The email address.
    :returns: Django's messages, translated; empty when it is valid.
    """
    try:
        validate_email(email)
    except DjangoValidationError as e:
        return list(e.messages)
    return []


def password_errors(password: str, user: User) -> list[str]:
    """
    The messages of a password that Django's password validators refuse.

    :param password: The password.
    :param user: Its user, so that a password like their email address is refused.
    :returns: The validators' messages, translated; empty when it is accepted.
    """
    try:
        validate_password(password, user=user)
    except DjangoValidationError as e:
        return list(e.messages)
    return []


@method_decorator(never_cache, name="dispatch")
class AccountApiView(SmarterView):
    """The base class of the account api's views: JSON bodies, and the credentials rate limit."""

    http_method_names = ["post"]

    def read_body(self, request: HttpRequest, model: type[RequestModel]) -> RequestModel:
        """
        The request's body, as the endpoint's model.

        :param request: The request, whose body is JSON.
        :param model: The endpoint's request model.
        :returns: The body.
        :raises InvalidRequest: when the body isn't JSON, or isn't the model.
        """
        try:
            data = json.loads(request.body or b"{}")
            return model.model_validate(data)
        except (ValueError, ValidationError) as e:
            raise InvalidRequest(str(e)) from e

    def throttle_credentials(self, request: HttpRequest) -> Optional[JsonResponse]:
        """
        Check the request against the credentials rate limit.

        :param request: The request.
        :returns: A 429 response if the address has made too many attempts, otherwise None.
        """
        wait = credentials_throttle_wait(request, self)
        if wait is None:
            return None
        return throttled_response(wait)


class SignInApiView(AccountApiView):
    """``POST /api/web/account/login/``: sign in with an email address and password."""

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Sign in, and answer with the new session.

        An unknown address and a wrong password get the same answer, so that it doesn't reveal which
        addresses have accounts.

        :param request: The request, whose body is a :class:`~smarter.apps.account.api.web.contract.SignInRequest`.
        :returns: The new session; 400 with :class:`~smarter.apps.account.api.web.contract.AccountErrors`;
            403 for the right password of an account that isn't activated yet; or 429.
        """
        throttled = self.throttle_credentials(request)
        if throttled is not None:
            return throttled
        try:
            body = self.read_body(request, SignInRequest)
        except InvalidRequest:
            return errors_response(_("The request is invalid."))
        user = sign_in_with_email(request, body.email, body.password)
        if user is not None:
            return session_response(request)
        if awaits_activation(body.email, body.password):
            # only someone who knows the password learns that the account is waiting.
            return errors_response(
                _("Your account isn't activated yet. Follow the link that we emailed you, or ask for a new one."),
                status=HTTPStatus.FORBIDDEN,
            )
        return errors_response(_("Email and/or password do not match."))


class SignOutApiView(AccountApiView):
    """``POST /api/web/account/logout/``: sign out."""

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Sign out, and answer with the visitor's session.

        :param request: The request.
        :returns: The session of a visitor who isn't signed in.
        """
        logout(request)
        return session_response(request)


class SignUpApiView(AccountApiView):
    """
    ``POST /api/web/account/register/``: create an inactive user, and email them an activation link.

    It answers 404 while the ``ENABLE_ACCOUNT_REGISTRATION`` switch is off, as the sign-up page does.
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Create the user, and email them a link to activate their account.

        :param request: The request, whose body is a :class:`~smarter.apps.account.api.web.contract.SignUpRequest`.
        :returns: 200 with an :class:`~smarter.apps.account.api.web.contract.AccountMessage`; 400 with the
            email's and password's errors; 404 while sign-up is switched off; 429; or 500 if the email
            can't be rendered.
        """
        if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_ACCOUNT_REGISTRATION):
            return errors_response(_("Registration is closed."), status=HTTPStatus.NOT_FOUND)
        throttled = self.throttle_credentials(request)
        if throttled is not None:
            return throttled
        try:
            body = self.read_body(request, SignUpRequest)
        except InvalidRequest:
            return errors_response(_("The request is invalid."))

        field_errors: dict[str, list[str]] = {}
        invalid_email = email_errors(body.email)
        if invalid_email:
            field_errors["email"] = invalid_email
        elif email_is_taken(body.email):
            field_errors["email"] = [_("An account with this email address already exists. Please sign in.")]
        # the password is checked against the would-be user, so that one like their address is refused.
        candidate = User(username=body.email, email=body.email)
        invalid_password = password_errors(body.password, candidate)
        if invalid_password:
            field_errors["password"] = invalid_password
        if field_errors:
            return errors_response(_("Please correct the errors below."), field_errors)

        try:
            sign_up(request, body.email, body.password)
        except RuntimeError:
            # the user exists, inactive, and can ask for a new link once the template is fixed.
            logger.error("%s.SignUpApiView.post() could not render the activation email.", logger_prefix)
            return unknown_error_response()
        return message_response(_("We have emailed you a link to activate your account. Follow it to sign in."))


class ActivateApiView(AccountApiView):
    """
    ``POST /api/web/account/activate/<uidb64>/<token>/``: activate an account with its emailed link, and sign in.

    The console serves the emailed link, ``/account/activate/<uidb64>/<token>/``, and calls this with its
    two parts. It isn't rate limited: the token is the credential, and a guess can't be checked faster than
    the password reset link's.
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Activate the link's user, sign them in, and answer with the new session.

        :param request: The request.
        :param kwargs: ``uidb64`` and ``token``.
        :returns: The new session, or 404, 403 or 400 for a link that can't be used.
        """
        try:
            activate(request, kwargs["uidb64"], kwargs["token"])
        except EmailLinkError as e:
            return link_error_response(e)
        return session_response(request)


class ActivationResendApiView(AccountApiView):
    """``POST /api/web/account/activation-resend/``: email a new activation link."""

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Email a new link to the address's inactive user, if they may activate by email.

        The answer is the same either way.

        :param request: The request, whose body is an
            :class:`~smarter.apps.account.api.web.contract.ActivationResendRequest`.
        :returns: 200 with an :class:`~smarter.apps.account.api.web.contract.AccountMessage`; 400 for an
            invalid address; 429; or 500 if the email can't be rendered.
        """
        throttled = self.throttle_credentials(request)
        if throttled is not None:
            return throttled
        try:
            body = self.read_body(request, ActivationResendRequest)
        except InvalidRequest:
            return errors_response(_("The request is invalid."))
        invalid_email = email_errors(body.email)
        if invalid_email:
            return errors_response(_("Please correct the errors below."), {"email": invalid_email})
        try:
            resend_activation_email(request, body.email)
        except RuntimeError:
            logger.error("%s.ActivationResendApiView.post() could not render the email.", logger_prefix)
            return unknown_error_response()
        # the same answer whether or not the address has an inactive account, so that it isn't revealed.
        return message_response(
            _("If an account with this email address is waiting to be activated, we have sent it a new link.")
        )


class PasswordResetRequestApiView(AccountApiView):
    """``POST /api/web/account/password-reset-request/``: email a password reset link."""

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Email a link to the user who has the address, if any, and answer the same either way.

        :param request: The request, whose body is a
            :class:`~smarter.apps.account.api.web.contract.PasswordResetRequest`.
        :returns: 200 with an :class:`~smarter.apps.account.api.web.contract.AccountMessage`; 400 for an
            invalid address; 429; or 500 if the email can't be rendered.
        """
        throttled = self.throttle_credentials(request)
        if throttled is not None:
            return throttled
        try:
            body = self.read_body(request, PasswordResetRequest)
        except InvalidRequest:
            return errors_response(_("The request is invalid."))
        invalid_email = email_errors(body.email)
        if invalid_email:
            return errors_response(_("Please correct the errors below."), {"email": invalid_email})
        try:
            send_password_reset_email(request, body.email)
        except RuntimeError:
            logger.error("%s.PasswordResetRequestApiView.post() could not render the email.", logger_prefix)
            return unknown_error_response()
        # the same answer whether or not a user has the address, so that it isn't revealed.
        return message_response(
            _("If an account has this email address, we have sent it a link to reset the password.")
        )


class PasswordResetApiView(AccountApiView):
    """
    ``/api/web/account/password-reset/<uidb64>/<token>/``: check an emailed link, and set a new password.

    The console serves the emailed link, ``/password-reset-link/<uidb64>/<token>/``, and calls this with
    its two parts.
    """

    http_method_names = ["get", "post"]

    def get(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Check that the link can be used, before the console asks for the new password.

        :param request: The request.
        :param kwargs: ``uidb64`` and ``token``.
        :returns: 200, or 404, 403 or 400 for a link that can't be used.
        """
        try:
            user_from_reset_link(kwargs["uidb64"], kwargs["token"])
        except EmailLinkError as e:
            return link_error_response(e)
        return message_response(_("Choose a new password."))

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Set the link's user's new password.

        :param request: The request, whose body is a
            :class:`~smarter.apps.account.api.web.contract.NewPasswordRequest`.
        :param kwargs: ``uidb64`` and ``token``.
        :returns: 200; 400 with the passwords' errors; or 404, 403 or 400 for a link that can't be used.
        """
        try:
            user = user_from_reset_link(kwargs["uidb64"], kwargs["token"])
        except EmailLinkError as e:
            return link_error_response(e)
        try:
            body = self.read_body(request, NewPasswordRequest)
        except InvalidRequest:
            return errors_response(_("The request is invalid."))
        if body.password != body.password_confirm:
            return errors_response(
                _("Please correct the errors below."),
                {"passwordConfirm": [_("Passwords do not match.")]},
            )
        invalid_password = password_errors(body.password, user)
        if invalid_password:
            return errors_response(_("Please correct the errors below."), {"password": invalid_password})
        user.set_password(body.password)
        user.save()
        logger.info("%s.PasswordResetApiView.post() reset the password of user %s", logger_prefix, user.pk)
        return message_response(_("Your password has been changed. Sign in with it."))
