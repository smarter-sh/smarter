# -*- coding: utf-8 -*-
# pylint: disable=C0115
"""Django views"""
import logging

from smarter.apps.common.view_helpers import SmarterAuthenticatedWebView


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Protected Views
# ------------------------------------------------------------------------------
class AccountView(SmarterAuthenticatedWebView):

    template_path = "account/account.html"


class AccountOrganizationView(SmarterAuthenticatedWebView):

    template_path = "account/organization.html"


class AccountTeamView(SmarterAuthenticatedWebView):

    template_path = "account/team.html"


class AccountLimitsView(SmarterAuthenticatedWebView):

    template_path = "account/limits.html"


class AccountProfileView(SmarterAuthenticatedWebView):

    template_path = "account/profile.html"


class AccountAPIKeysView(SmarterAuthenticatedWebView):
    """API keys view"""

    template_path = "dashboard/api-keys.html"


class AccountUsageView(SmarterAuthenticatedWebView):
    """Usage view"""

    template_path = "dashboard/usage.html"
