"""Django password management views."""

import logging
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect

from smarter.apps.account.models import UserClass as User
from smarter.apps.account.models import get_resolved_user
from smarter.common.classes import SmarterHelperMixin
from smarter.common.helpers.email_helpers import email_helper
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
from smarter.lib.django.view_helpers import SmarterNeverCachedWebView


logger = logging.getLogger(__name__)


class PasswordResetRequestView(SmarterNeverCachedWebView):
    """View for requesting a password reset email."""

    expiring_token = ExpiringTokenGenerator()

    class EmailForm(forms.Form):
        """Form for the sign-in page."""

        email = forms.EmailField()

    template_path = "account/authentication/password-reset-request.html"
    email_template_path = "account/authentication/email/password-reset.html"

    def get(self, request):
        form = PasswordResetRequestView.EmailForm()
        context = {"form": form}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request):
        form = PasswordResetRequestView.EmailForm(request.POST)
        if not form.is_valid():
            return SmarterHttpResponseBadRequest(request=request, error_message="Email address is invalid.")
        email = form.cleaned_data["email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Do not reveal if the email is not in the system.
            return HttpResponse("", status=HTTPStatus.OK.value)

        password_reset_link = self.expiring_token.encode_link(
            request=request, user=user, reverse_link="account:password_reset_link"
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
        logger.info("%s.get() begin", self.formatted_class_name)
        form = PasswordResetView.NewPasswordForm()
        uidb64 = kwargs.get("uidb64", None)
        token = kwargs.get("token", None)

        logger.info("%s.get() initialized", self.formatted_class_name)
        try:
            user = self.expiring_token.decode_link(uidb64=uidb64, token=token)
            logger.info("%s.get() user: %s", self.formatted_class_name, user)
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

        logger.info("%s.get() finalizing", self.formatted_class_name)
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
