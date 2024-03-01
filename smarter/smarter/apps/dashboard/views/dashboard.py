# -*- coding: utf-8 -*-
# pylint: disable=W0613
"""Django views"""
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control

from smarter.view_helpers import clean_http_response


logger = logging.getLogger(__name__)


@login_required
@cache_control(max_age=settings.SMARTER_CACHE_EXPIRATION)
def dashboard(request):
    logger.info("Dashboard view")
    return clean_http_response(template_path="dashboard/dashboard.html")


@login_required
@cache_control(max_age=settings.SMARTER_CACHE_EXPIRATION)
def api_keys(request):
    logger.info("API keys view")
    return clean_http_response(template_path="dashboard/api-keys.html")


@login_required
@cache_control(max_age=settings.SMARTER_CACHE_EXPIRATION)
def plugins(request):
    logger.info("Plugins view")
    return clean_http_response(template_path="dashboard/plugins.html")


@login_required
@cache_control(max_age=settings.SMARTER_CACHE_EXPIRATION)
def usage(request):
    logger.info("Usage view")
    return clean_http_response(template_path="dashboard/usage.html")


@login_required
@cache_control(max_age=settings.SMARTER_CACHE_EXPIRATION)
def documentation(request):
    logger.info("Documentation view")
    return clean_http_response(template_path="dashboard/documentation.html")


@login_required
@cache_control(max_age=settings.SMARTER_CACHE_EXPIRATION)
def platform_help(request):
    logger.info("Help view")
    return clean_http_response(template_path="dashboard/help.html")


@login_required
@cache_control(max_age=settings.SMARTER_CACHE_EXPIRATION)
def notifications(request):
    logger.info("Notifications view")
    return clean_http_response(template_path="dashboard/notifications.html")
