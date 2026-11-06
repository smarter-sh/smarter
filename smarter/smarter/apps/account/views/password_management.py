"""Django password management views."""

from http import HTTPStatus

from django import forms
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import gettext as _

from smarter.apps.account.password_reset import (
    PasswordResetLinkError,
    password_reset_link,
    send_password_reset_email,
    user_from_reset_link,
)
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib import logging
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseBadRequest,
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
)
from smarter.lib.django.views import SmarterNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


def link_error_response(request, error: PasswordResetLinkError) -> HttpResponse:
    """
    The error page of a password reset link that can't be used.

    :param request: The request.
    :param error: Why the link can't be used.
    :returns: A 404, 403 or 400 page.
    """
    message = str(error)
    if error.status == HTTPStatus.NOT_FOUND:
        return SmarterHttpResponseNotFound(request=request, error_message=message)
    if error.status == HTTPStatus.FORBIDDEN:
        return SmarterHttpResponseForbidden(request=request, error_message=message)
    return SmarterHttpResponseBadRequest(request=request, error_message=message)


# pylint: disable=W0613
class PasswordResetRequestView(SmarterNeverCachedWebView):
    """View for requesting a password reset email."""

    class EmailForm(forms.Form):
        """Form for the sign-in page."""

        email = forms.EmailField()

    template_path = "account/authentication/password-reset-request.html"
    email_template_path = "account/authentication/email/password-reset.html"
    password_reset_link: str = ""

    def generate_password_reset_link(self, request, user):
        """
        Generate a password reset link for the given user.

        See :func:`smarter.apps.account.password_reset.password_reset_link`.

        :param request: The request, for the link's host.
        :param user: The User.
        :returns: The link.
        :raises SmarterValueError: when ``user`` is not a User.
        """
        return password_reset_link(request, user)

    def get(self, request, *args, **kwargs):
        """
        Render the form that asks for the email address.

        :param request: The request.
        :returns: The rendered form.
        """
        form = PasswordResetRequestView.EmailForm()
        context = {"form": form}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request, *args, **kwargs):
        """
        Email a password reset link to the user with the form's email address.

        The response is the same whether or not a user has the address, so that it isn't revealed.

        :param request: The request, with the form's data.
        :returns: A 200 response, or a 400 one for an invalid address.
        """
        form = PasswordResetRequestView.EmailForm(request.POST)
        if not form.is_valid():
            return SmarterHttpResponseBadRequest(request=request, error_message=_("Email address is invalid."))
        email = form.cleaned_data["email"]
        try:
            send_password_reset_email(request, email)
        except RuntimeError:
            return HttpResponse(status=HTTPStatus.INTERNAL_SERVER_ERROR.value)
        # the same answer whether or not a user has the address, so that it isn't revealed.
        return HttpResponse(_("Email sent."), status=HTTPStatus.OK.value)


class PasswordResetView(SmarterNeverCachedWebView, SmarterHelperMixin):
    """View for resetting password."""

    template_path = "account/authentication/new-password.html"
    uidb64: str = ""
    token: str = ""

    class NewPasswordForm(forms.Form):
        """Form for the sign-in page."""

        password = forms.CharField(widget=forms.PasswordInput)
        password_confirm = forms.CharField(widget=forms.PasswordInput)

    # pylint: disable=unused-argument
    def get(self, request, *args, **kwargs):
        """
        Render the new password form for a password reset link.

        :param request: The request.
        :param kwargs: ``uidb64`` and ``token``, from the link.
        :returns: The rendered form, or a 400, 403 or 404 response when the link is not valid.
        """
        logger.debug("%s.get() begin", self.formatted_class_name)
        form = PasswordResetView.NewPasswordForm()
        try:
            self.uidb64 = kwargs["uidb64"]
            self.token = kwargs["token"]
        except KeyError:
            return SmarterHttpResponseBadRequest(request=request, error_message=_("Missing uidb64 or token in URL."))

        logger.debug("%s.get() initialized", self.formatted_class_name)
        try:
            user = user_from_reset_link(self.uidb64, self.token)
        except PasswordResetLinkError as e:
            return link_error_response(request, e)

        logger.debug("%s.get() finalizing", self.formatted_class_name)
        context = {"form": form, "password_reset": {"uidb64": self.uidb64, "token": self.token, "user": user}}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request, *args, **kwargs):
        """
        Set the user's new password from the form, and redirect to the login page.

        :param request: The request, with the form's data.
        :param kwargs: ``uidb64`` and ``token``, from the link.
        :returns: The redirect, or a 400, 403 or 404 response when the form or the link is not valid.
        """
        try:
            self.uidb64 = kwargs["uidb64"]
            self.token = kwargs["token"]
        except KeyError:
            return SmarterHttpResponseBadRequest(request=request, error_message=_("Missing uidb64 or token in URL."))

        form = PasswordResetView.NewPasswordForm(request.POST)
        if not form.is_valid():
            return SmarterHttpResponseBadRequest(request=request, error_message=_("input form is invalid."))

        password = form.cleaned_data["password"]
        password_confirm = form.cleaned_data["password_confirm"]

        if password != password_confirm:
            return SmarterHttpResponseBadRequest(request=request, error_message=_("Passwords do not match."))

        try:
            user = user_from_reset_link(self.uidb64, self.token)
        except PasswordResetLinkError as e:
            return link_error_response(request, e)

        user.set_password(password)
        user.save()
        return redirect(settings.LOGIN_URL)
