# -*- coding: utf-8 -*-
# pylint: disable=W0613
"""Django REST framework views for the API admin app."""
from django import forms
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import HttpResponse, redirect

from smarter.email_helpers import EmailHelper
from smarter.view_helpers import (
    SmarterAuthenticatedWebView,
    SmarterWebView,
    redirect_and_expire_cache,
)


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class LoginView(SmarterWebView):
    """View for logging in browser session."""

    class LoginForm(forms.Form):
        """Form for the sign-in page."""

        email = forms.EmailField()
        password = forms.CharField(widget=forms.PasswordInput)

    template_path = "account/authentication/sign-in.html"

    def get(self, request):
        form = LoginView.LoginForm()
        context = {"form": form}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request):
        form = LoginView.LoginForm(request.POST)
        authenticated_user: User = None
        if form.is_valid():
            email = form.cleaned_data["email"]
            try:
                user = User.objects.get(email=form.cleaned_data["email"])
                password = form.cleaned_data["password"]
                authenticated_user = authenticate(request, username=user.username, password=password)
                if authenticated_user is not None:
                    login(request, authenticated_user)
                    return redirect("/")
                return HttpResponse("Username and/or password do not match.", status=401)
            except User.DoesNotExist:
                return HttpResponse(f"Invalid login attempt. Unknown user {email}", status=403)
            # pylint: disable=W0718
            except Exception as e:
                return HttpResponse(f"An unknown error occurred {e.description}", status=500)
        return HttpResponse("Received invalid responses.", status=400)


class LogoutView(SmarterWebView):
    """View for logging out browser session."""

    def get(self, request):
        logout(request)
        return redirect("/")

    def post(self, request):
        logout(request)
        return redirect_and_expire_cache(path="/")


class ResetPasswordView(SmarterWebView):
    """View for resetting password."""

    class EmailForm(forms.Form):
        """Form for the sign-in page."""

        email = forms.EmailField()

    template_path = "account/authentication/reset-password.html"
    email_template_path = "account/authentication/email/reset-password.html"

    def get(self, request):
        form = ResetPasswordView.EmailForm()
        context = {"form": form}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request):
        print("ResetPasswordView.post(): ")
        form = ResetPasswordView.EmailForm(request.POST)
        if not form.is_valid():
            return HttpResponse("Email address is invalid.", status=400)

        email = form.cleaned_data["email"]
        body = self.render_clean_html(request, template_path=self.email_template_path)
        subject = "Reset your password"
        to = email
        EmailHelper.send_email(subject=subject, body=body, to=to, html=True)
        return HttpResponse("Email sent.", status=200)


class NewPasswordView(SmarterWebView):
    """View for resetting password."""

    template_path = "account/authentication/new-password.html"


class ConfirmPasswordView(SmarterWebView):
    """View for resetting password."""

    template_path = "account/authentication/password-confirmation.html"


class SignUpView(SmarterWebView):
    """View for signing up."""

    class SignUpForm(forms.Form):
        """Form for the sign-in page."""

        email = forms.EmailField()
        password = forms.CharField(widget=forms.PasswordInput)

    template_path = "account/authentication/sign-up.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect_and_expire_cache(path="/")

        form = SignUpView.SignUpForm()
        context = {"form": form}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request):
        form = SignUpView.SignUpForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = User.objects.create_user(username, password=password)
            login(request, user)
            return redirect_and_expire_cache(path="/welcome/")
        return self.get(request=request)


class VerifyEmailView(SmarterWebView):
    """View for verifying email."""

    template_path = "account/authentication/verify-email.html"


# ------------------------------------------------------------------------------
# Private Access Views
# ------------------------------------------------------------------------------
class WelcomeView(SmarterAuthenticatedWebView):
    """View for the welcome page."""

    template_path = "account/welcome.html"


class AccountDeactivateView(SmarterAuthenticatedWebView):
    """View for the account deactivation page."""

    template_path = "account/account-deactivated.html"
