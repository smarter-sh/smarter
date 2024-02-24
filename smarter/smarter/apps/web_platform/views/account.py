# -*- coding: utf-8 -*-
"""Django views"""
import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


logger = logging.getLogger(__name__)


@login_required
def account(request):
    logger.info("Account view")
    return render(request, "account/account.html")


@login_required
def account_organization(request):
    logger.info("Account-organization view")
    return render(request, "account/organization.html")


@login_required
def account_team(request):
    logger.info("Account-team view")
    return render(request, "account/team.html")


@login_required
def account_limits(request):
    logger.info("Account-limits view")
    return render(request, "account/limits.html")


@login_required
def account_profile(request):
    logger.info("Account-profile view")
    return render(request, "account/profile.html")
