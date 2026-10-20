"""
The account dashboard: the deprecated Account UI, and the profile image view.

The Account UI's urls are disabled. See :mod:`smarter.apps.account.views.dashboard.urls`.
"""

ACCOUNT_UI_DEPRECATION_MESSAGE = (
    "The Account UI at /dashboard/account/dashboard/ is deprecated, and its urls are disabled. "
    "See smarter.apps.account.views.dashboard.urls."
)
"""The message of the ``@deprecated`` decorator on each view of the Account UI."""
