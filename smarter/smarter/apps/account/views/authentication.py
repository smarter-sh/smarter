# -*- coding: utf-8 -*-
# pylint: disable=W0613
"""Django REST framework views for the API admin app."""
from django import forms
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect

from smarter.view_helpers import SmarterWebView, redirect_and_expire_cache


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
        if form.is_valid():
            user = authenticate(request, username=form.cleaned_data["email"], password=form.cleaned_data["password"])
            if user is not None:
                login(request, user)
                return redirect("/")

        return self.get(request=request)


class LogoutView(SmarterWebView):
    """View for logging out browser session."""

    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect("/")

    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect_and_expire_cache(path="/")


class ResetPasswordView(SmarterWebView):
    """View for resetting password."""

    template_path = "account/authentication/reset-password.html"


class NewPasswordView(SmarterWebView):
    """View for resetting password."""

    template_path = "account/authentication/new-password.html"


class SignUpView(SmarterWebView):
    """View for signing up."""

    template_path = "account/authentication/sign-up.html"
