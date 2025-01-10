# pylint: disable=C0115
"""Django views"""
import logging

from smarter.lib.django.view_helpers import SmarterAuthenticatedNeverCachedWebView


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Protected Views
# ------------------------------------------------------------------------------


class AccountOrganizationView(SmarterAuthenticatedNeverCachedWebView):

    template_path = "account/organization.html"


class AccountTeamView(SmarterAuthenticatedNeverCachedWebView):

    template_path = "account/team.html"


class AccountLimitsView(SmarterAuthenticatedNeverCachedWebView):

    template_path = "account/limits.html"


class AccountProfileView(SmarterAuthenticatedNeverCachedWebView):

    template_path = "account/profile.html"


class AccountAPIKeysView(SmarterAuthenticatedNeverCachedWebView):
    """API keys view"""

    template_path = "dashboard/api-keys.html"


class AccountUsageView(SmarterAuthenticatedNeverCachedWebView):
    """Usage view"""

    template_path = "dashboard/usage.html"
