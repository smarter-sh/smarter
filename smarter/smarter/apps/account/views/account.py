# pylint: disable=C0115
"""Django views"""

from smarter.lib import logging
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


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
