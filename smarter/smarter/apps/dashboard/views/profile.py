# -*- coding: utf-8 -*-
# pylint: disable=C0115
"""Django views"""
import logging

from smarter.view_helpers import SmarterAuthenticatedWebView


logger = logging.getLogger(__name__)


class ProfileView(SmarterAuthenticatedWebView):

    template_path = "dashboard-default.html"


class ProfileLanguageView(SmarterAuthenticatedWebView):

    template_path = "dashboard-default.html"
