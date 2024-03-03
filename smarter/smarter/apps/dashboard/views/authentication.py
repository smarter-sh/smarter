# -*- coding: utf-8 -*-
# pylint: disable=W0613
"""Django REST framework views for the API admin app."""
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from rest_framework.permissions import AllowAny

from smarter.view_helpers import SmarterAPIView


def login_redirector(request):
    return redirect(settings.LOGIN_URL)


class LogoutView(SmarterAPIView):
    """View for logging out browser session."""

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect("/")

    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect("/")
