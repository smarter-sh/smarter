# -*- coding: utf-8 -*-
"""Django password management views."""
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import HttpResponse, redirect
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from smarter.email_helpers import EmailHelper
from smarter.token_generators import (
    ExpiringTokenGenerator,
    TokenConversionError,
    TokenExpiredError,
    TokenIntegrityError,
    TokenParseError,
)
from smarter.view_helpers import SmarterWebView


RESET_LINK_EXPIRATION = 86400
password_reset_token = ExpiringTokenGenerator()


class PasswordResetRequestView(SmarterWebView):
    """View for requesting a password reset email."""

    class EmailForm(forms.Form):
        """Form for the sign-in page."""

        email = forms.EmailField()

    template_path = "account/authentication/password-reset-request.html"
    email_template_path = "account/authentication/email/password-reset.html"

    def get_password_reset_link(self, user, request):
        print("PasswordResetRequestView.get_password_reset_link()")
        token = password_reset_token.make_token(user=user)
        domain = get_current_site(request).domain
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        link = reverse("password_reset_link", kwargs={"uidb64": uid, "token": token})
        protocol = "https" if request.is_secure() else "http"
        url = protocol + "://" + domain + link
        return url

    def get(self, request):
        form = PasswordResetRequestView.EmailForm()
        context = {"form": form}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request):
        form = PasswordResetRequestView.EmailForm(request.POST)
        if not form.is_valid():
            return HttpResponse("Email address is invalid.", status=400)
        email = form.cleaned_data["email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Do not reveal if the email is not in the system.
            return HttpResponse("", status=200)

        password_reset_link = self.get_password_reset_link(user=user, request=request)
        context = {"password_reset": {"url": password_reset_link}}
        body = self.render_clean_html(request, template_path=self.email_template_path, context=context)
        subject = "Reset your password"
        to = email
        EmailHelper.send_email(subject=subject, body=body, to=to, html=True)
        return HttpResponse("Email sent.", status=200)


class PasswordResetView(SmarterWebView):
    """View for resetting password."""

    template_path = "account/authentication/new-password.html"

    class NewPasswordForm(forms.Form):
        """Form for the sign-in page."""

        password = forms.CharField(widget=forms.PasswordInput)
        password_confirm = forms.CharField(widget=forms.PasswordInput)

    def get_user_and_validate(self, uidb64, token) -> User:
        """Get the user from the uid and token and validate."""
        uid = urlsafe_base64_decode(uidb64)
        user = User.objects.get(pk=uid)
        password_reset_token.validate(user, token, expiration=RESET_LINK_EXPIRATION)
        return user

    # pylint: disable=unused-argument
    def get(self, request, *args, **kwargs):
        user: User = None
        form = PasswordResetView.NewPasswordForm()
        uidb64 = kwargs.get("uidb64", None)
        token = kwargs.get("token", None)

        try:
            user = self.get_user_and_validate(uidb64, token)
        except User.DoesNotExist:
            return HttpResponse("Invalid password reset link. User does not exist.", status=404)
        except (TypeError, ValueError, OverflowError, TokenParseError, TokenConversionError, TokenIntegrityError) as e:
            return HttpResponse(e, status=400)
        except TokenExpiredError as e:
            return HttpResponse(e, status=401)

        context = {"form": form, "password_reset": {"uidb64": uidb64, "token": token, "user": user}}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request, *args, **kwargs):
        uidb64 = kwargs.get("uidb64", None)
        token = kwargs.get("token", None)
        form = PasswordResetView.NewPasswordForm(request.POST)
        if not form.is_valid():
            return HttpResponse("input form is invalid.", status=400)

        password = form.cleaned_data["password"]
        password_confirm = form.cleaned_data["password_confirm"]

        if password != password_confirm:
            print("Passwords do not match.")
            return HttpResponse("Passwords do not match.", status=400)

        try:
            user = self.get_user_and_validate(uidb64, token)
        except User.DoesNotExist:
            return HttpResponse("Invalid password reset link. User does not exist.", status=404)
        except (TypeError, ValueError, OverflowError, TokenParseError, TokenConversionError, TokenIntegrityError) as e:
            return HttpResponse(e, status=400)
        except TokenExpiredError as e:
            return HttpResponse(e, status=401)

        user.set_password(password)
        user.save()
        return redirect(settings.LOGIN_URL)


class PasswordConfirmView(SmarterWebView):
    """View for resetting password."""

    template_path = "account/authentication/password-confirmation.html"
