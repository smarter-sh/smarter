# -*- coding: utf-8 -*-
# pylint: disable=C0115
"""Django views"""
import logging

from smarter.view_helpers import SmarterAPIAdminView


logger = logging.getLogger(__name__)


class AccountView(SmarterAPIAdminView):

    template_path = "account/account.html"


class AccountOrganizationView(SmarterAPIAdminView):

    template_path = "account/organization.html"


class AccountTeamView(SmarterAPIAdminView):

    template_path = "account/team.html"


class AccountLimitsView(SmarterAPIAdminView):

    template_path = "account/limits.html"


class AccountProfileView(SmarterAPIAdminView):

    template_path = "account/profile.html"
