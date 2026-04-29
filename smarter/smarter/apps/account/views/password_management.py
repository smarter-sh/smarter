"""Django password management views."""

from http import HTTPStatus

from django import forms
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect

import smarter.lib.logging as logging
from smarter.apps.account.models import User
from smarter.apps.account.urls import AccountNamedUrls
from smarter.common.helpers.email_helpers import email_helper
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseBadRequest,
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
)
from smarter.lib.django.token_generators import (
    ExpiringTokenGenerator,
    SmarterTokenConversionError,
    SmarterTokenExpiredError,
    SmarterTokenIntegrityError,
    SmarterTokenParseError,
)
from smarter.lib.django.views import SmarterNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


class PasswordResetRequestView(SmarterNeverCachedWebView):
    """View for requesting a password reset email."""

    expiring_token = ExpiringTokenGenerator()

    class EmailForm(forms.Form):
        """Form for the sign-in page."""

        email = forms.EmailField()

    template_path = "account/authentication/password-reset-request.html"
    email_template_path = "account/authentication/email/password-reset.html"

    def get(self, request, *args, **kwargs):
        form = PasswordResetRequestView.EmailForm()
        context = {"form": form}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request, *args, **kwargs):
        form = PasswordResetRequestView.EmailForm(request.POST)
        if not form.is_valid():
            return SmarterHttpResponseBadRequest(request=request, error_message="Email address is invalid.")
        email = form.cleaned_data["email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Do not reveal if the email is not in the system.
            return HttpResponse("", status=HTTPStatus.OK.value)
        except User.MultipleObjectsReturned:
            # In the rare case that multiple users have the same email, we can still send the reset email to one of them.
            logger.warning("Multiple users found with email %s. Sending password reset email to one of them.", email)
            user = User.objects.filter(email=email).first()

        password_reset_link = self.expiring_token.encode_link(
            request=request, user=user, reverse_link=AccountNamedUrls.PASSWORD_RESET_LINK
        )
        context = {"password_reset": {"url": password_reset_link}}
        body = self.render_clean_html(request, template_path=self.email_template_path, context=context)
        subject = "Reset your password"
        to = email
        email_helper.send_email(subject=subject, body=body, to=to, html=True)
        return HttpResponse("Email sent.", status=HTTPStatus.OK.value)


class PasswordResetView(SmarterNeverCachedWebView, SmarterHelperMixin):
    """View for resetting password."""

    template_path = "account/authentication/new-password.html"
    expiring_token = ExpiringTokenGenerator()

    class NewPasswordForm(forms.Form):
        """Form for the sign-in page."""

        password = forms.CharField(widget=forms.PasswordInput)
        password_confirm = forms.CharField(widget=forms.PasswordInput)

    # pylint: disable=unused-argument
    def get(self, request, *args, **kwargs):
        logger.debug("%s.get() begin", self.formatted_class_name)
        form = PasswordResetView.NewPasswordForm()
        uidb64 = kwargs.get("uidb64", None)
        token = kwargs.get("token", None)

        logger.debug("%s.get() initialized", self.formatted_class_name)
        try:
            user = self.expiring_token.decode_link(uidb64=uidb64, token=token)
            logger.debug("%s.get() user: %s", self.formatted_class_name, user)
        except User.DoesNotExist:
            return SmarterHttpResponseNotFound(
                request=request, error_message="Invalid password reset link. User does not exist."
            )
        except (
            TypeError,
            ValueError,
            OverflowError,
            SmarterTokenParseError,
            SmarterTokenConversionError,
            SmarterTokenIntegrityError,
        ) as e:
            return SmarterHttpResponseBadRequest(request=request, error_message=str(e))
        except SmarterTokenExpiredError as e:
            return SmarterHttpResponseForbidden(request=request, error_message=str(e))

        logger.debug("%s.get() finalizing", self.formatted_class_name)
        context = {"form": form, "password_reset": {"uidb64": uidb64, "token": token, "user": user}}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request, *args, **kwargs):
        uidb64 = kwargs.get("uidb64", None)
        token = kwargs.get("token", None)
        form = PasswordResetView.NewPasswordForm(request.POST)
        if not form.is_valid():
            return SmarterHttpResponseBadRequest(request=request, error_message="input form is invalid.")

        password = form.cleaned_data["password"]
        password_confirm = form.cleaned_data["password_confirm"]

        if password != password_confirm:
            return SmarterHttpResponseBadRequest(request=request, error_message="Passwords do not match.")

        try:
            user = self.expiring_token.decode_link(uidb64, token)
        except User.DoesNotExist:
            return SmarterHttpResponseNotFound(
                request=request, error_message="Invalid password reset link. User does not exist."
            )
        except (
            TypeError,
            ValueError,
            OverflowError,
            SmarterTokenParseError,
            SmarterTokenConversionError,
            SmarterTokenIntegrityError,
        ) as e:
            return SmarterHttpResponseBadRequest(request=request, error_message=str(e))
        except SmarterTokenExpiredError as e:
            return SmarterHttpResponseForbidden(request=request, error_message=str(e))

        user.set_password(password)
        user.save()
        return redirect(settings.LOGIN_URL)


class PasswordConfirmView(SmarterNeverCachedWebView):
    """View for resetting password."""

    template_path = "account/authentication/password-confirmation.html"
