# -*- coding: utf-8 -*-
"""Django views"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from smarter.view_helpers import SmarterAuthenticatedWebView


@login_required
def chatapp(request):
    return render(request, "index.html")


class ChatAppView(SmarterAuthenticatedWebView):
    """Chat app view for smarter web."""

    template_path = "index.html"
