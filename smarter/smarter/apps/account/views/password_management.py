"""Django password management views."""

import logging
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.shortcuts import HttpResponse, redirect

from smarter.common.classes import SmarterHelperMixin
from smarter.common.helpers.email_helpers import email_helper
from smarter.lib.django.token_generators import (
    ExpiringTokenGenerator,
    TokenConversionError,
    TokenExpiredError,
    TokenIntegrityError,
    TokenParseError,
)
from smarter.lib.django.user import User, UserType
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
            return HttpResponse("Email address is invalid.", status=HTTPStatus.BAD_REQUEST)
        email = form.cleaned_data["email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Do not reveal if the email is not in the system.
            return HttpResponse("", status=200)

        password_reset_link = self.expiring_token.encode_link(
            request=request, user=user, reverse_link="password_reset_link"
        )
        context = {"password_reset": {"url": password_reset_link}}
        body = self.render_clean_html(request, template_path=self.email_template_path, context=context)
        subject = "Reset your password"
        to = email
        email_helper.send_email(subject=subject, body=body, to=to, html=True)
        return HttpResponse("Email sent.", status=200)


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
        user: UserType = None
        form = PasswordResetView.NewPasswordForm()
        uidb64 = kwargs.get("uidb64", None)
        token = kwargs.get("token", None)

        logger.info("%s.get() initialized", self.formatted_class_name)
        try:
            user = self.expiring_token.decode_link(uidb64=uidb64, token=token)
            logger.info("%s.get() user: %s", self.formatted_class_name, user)
        except User.DoesNotExist:
            return HttpResponse("Invalid password reset link. User does not exist.", status=404)
        except (TypeError, ValueError, OverflowError, TokenParseError, TokenConversionError, TokenIntegrityError) as e:
            return HttpResponse(e, status=HTTPStatus.BAD_REQUEST)
        except TokenExpiredError as e:
            return HttpResponse(e, status=HTTPStatus.UNAUTHORIZED)

        logger.info("%s.get() finalizing", self.formatted_class_name)
        context = {"form": form, "password_reset": {"uidb64": uidb64, "token": token, "user": user}}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request, *args, **kwargs):
        uidb64 = kwargs.get("uidb64", None)
        token = kwargs.get("token", None)
        form = PasswordResetView.NewPasswordForm(request.POST)
        if not form.is_valid():
            return HttpResponse("input form is invalid.", status=HTTPStatus.BAD_REQUEST)

        password = form.cleaned_data["password"]
        password_confirm = form.cleaned_data["password_confirm"]

        if password != password_confirm:
            return HttpResponse("Passwords do not match.", status=HTTPStatus.BAD_REQUEST)

        try:
            user = self.expiring_token.decode_link(uidb64, token)
        except User.DoesNotExist:
            return HttpResponse("Invalid password reset link. User does not exist.", status=404)
        except (TypeError, ValueError, OverflowError, TokenParseError, TokenConversionError, TokenIntegrityError) as e:
            return HttpResponse(e, status=HTTPStatus.BAD_REQUEST)
        except TokenExpiredError as e:
            return HttpResponse(e, status=HTTPStatus.UNAUTHORIZED)

        user.set_password(password)
        user.save()
        return redirect(settings.LOGIN_URL)


class PasswordConfirmView(SmarterNeverCachedWebView):
    """View for resetting password."""

    template_path = "account/authentication/password-confirmation.html"
