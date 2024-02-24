# -*- coding: utf-8 -*-
"""Django views"""
import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


logger = logging.getLogger(__name__)


@login_required
def dashboard(request):
    logger.info("Dashboard view")
    return render(request, "dashboard/dashboard.html")


@login_required
def api_keys(request):
    logger.info("API keys view")
    return render(request, "dashboard/api-keys.html")


@login_required
def plugins(request):
    logger.info("Plugins view")
    return render(request, "dashboard/plugins.html")


@login_required
def usage(request):
    logger.info("Usage view")
    return render(request, "dashboard/usage.html")


@login_required
def documentation(request):
    logger.info("Documentation view")
    return render(request, "dashboard/documentation.html")


@login_required
def platform_help(request):
    logger.info("Help view")
    return render(request, "dashboard/help.html")


@login_required
def notifications(request):
    logger.info("Notifications view")
    return render(request, "dashboard/notifications.html")
