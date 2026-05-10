"""
Django Account Authentication Social Auth views.
"""

from django.http import HttpResponse

from smarter.lib import logging
from smarter.lib.django.views import (
    SmarterNeverCachedWebView,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING, SmarterWaffleSwitches.VIEW_LOGGING]
)


class SocialAuthAlreadyAssociatedView(SmarterNeverCachedWebView):
    """View for social auth account already associated page."""

    template_path = "account/authentication/social-auth-already-associated.html"

    def get(self, request, *args, **kwargs) -> HttpResponse:
        logger.debug(
            "%s.SocialAuthAlreadyAssociatedView.get() called with request type: %s %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            type(request),
            request,
            args,
            kwargs,
        )
        return self.clean_http_response(request, template_path=self.template_path)
