# pylint: disable=C0115
"""Django views"""
import logging

from smarter.lib.django import waffle
from smarter.lib.django.view_helpers import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING) and level <= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


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
