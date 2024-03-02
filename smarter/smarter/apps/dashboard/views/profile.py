# -*- coding: utf-8 -*-
"""Django views"""
import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


logger = logging.getLogger(__name__)


@login_required
def profile(request):
    logger.info("Profile view")
    return render(request, "dashboard-default.html")


@login_required
def language(request):
    logger.info("Language view")
    return render(request, "dashboard-default.html")


@login_required
def sign_out(request):
    logger.info("Sign Out view")
    return render(request, "dashboard-default.html")
