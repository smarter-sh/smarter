# -*- coding: utf-8 -*-
# pylint: disable=W0613
"""Django REST framework views for the API admin app."""
from django.contrib.auth import logout
from django.shortcuts import redirect, render
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView


def custom_api_root(request):
    return render(request, "rest_framework/root_page_template_v0.html")


class LogoutView(APIView):
    """View for logging out browser session."""

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect("/")

    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect("/")
