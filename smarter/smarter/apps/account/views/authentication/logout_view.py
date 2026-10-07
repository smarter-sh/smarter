"""
Django Account Authentication Logout view.
"""

from django.contrib.auth import logout
from django.http import HttpResponseRedirect

from smarter.lib import logging
from smarter.lib.django.views import (
    SmarterNeverCachedWebView,
    redirect_and_expire_cache,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING, SmarterWaffleSwitches.VIEW_LOGGING]
)


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class LogoutView(SmarterNeverCachedWebView):
    """View for logging out browser session."""

    def get(self, request, *args, **kwargs) -> HttpResponseRedirect:
        logger.debug(
            "%s.LogoutView.get() called with request type: %s %s with args: %s, kwargs: %s",
            self.formatted_class_name,
            type(request),
            request,
            args,
            kwargs,
        )
        logout(request)
        return redirect_and_expire_cache(path="/")

    def post(self, request, *args, **kwargs) -> HttpResponseRedirect:
        logger.debug(
            "%s.LogoutView.post() called with request type: %s %s with args: %s, kwargs: %s",
            self.formatted_class_name,
            type(request),
            request,
            args,
            kwargs,
        )
        logout(request)
        return redirect_and_expire_cache(path="/")
