# -*- coding: utf-8 -*-
# pylint: disable=W0613
"""Django REST framework views for the API admin app."""
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect

from smarter.view_helpers import SmarterWebView, redirect_and_expire_cache


class LoginRedirectView(SmarterWebView):
    """View for redirecting to login page."""

    def get(self, request, *args, **kwargs):
        return redirect(settings.LOGIN_URL)

    def post(self, request, *args, **kwargs):
        return redirect(settings.LOGIN_URL)


class LogoutView(SmarterWebView):
    """View for logging out browser session."""

    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect("/")

    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect_and_expire_cache(path="/")
