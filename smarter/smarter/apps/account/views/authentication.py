# -*- coding: utf-8 -*-
# pylint: disable=W0613
"""Django REST framework views for the API admin app."""
from django.contrib.auth import logout
from django.shortcuts import redirect

from smarter.view_helpers import SmarterWebView, redirect_and_expire_cache


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class LoginView(SmarterWebView):
    """View for logging in browser session."""

    template_path = "account/authentication/sign-in.html"


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
