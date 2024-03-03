# -*- coding: utf-8 -*-
# pylint: disable=C0115
"""Django views"""
import logging

from smarter.view_helpers import SmarterAPIAdminView


logger = logging.getLogger(__name__)


class ProfileView(SmarterAPIAdminView):

    template_path = "dashboard-default.html"


class ProfileLanguageView(SmarterAPIAdminView):

    template_path = "dashboard-default.html"
