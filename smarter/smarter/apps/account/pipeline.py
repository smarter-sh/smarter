"""
Authentication pipeline functions for account management.
"""

from django.shortcuts import redirect

from smarter.apps.account.urls import AccountNamedUrls


# pylint: disable=unused-argument
def redirect_inactive_account(strategy, details, *args, user=None, **kwargs):
    """
    This is used in settings.SOCIAL_AUTH_PIPELINE when running a
    multitenant setup.

    A pipeline function to redirect users with inactive accounts
    (e.g., payment inactive) to a custom page.
    """
    request = strategy.request if hasattr(strategy, "request") else None
    if request and request.session.get("account_status") == "inactive":
        # clear the flag so it doesn't persist
        del request.session["account_status"]
        return redirect(AccountNamedUrls.ACCOUNT_INACTIVE)
    # Continue the pipeline as normal
    return None
