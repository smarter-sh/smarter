# pylint: disable=W0707,W0718
"""Account views for smarter api."""
import logging

from smarter.apps.account.models import User, UserProfile
from smarter.apps.account.serializers import AccountSerializer
from smarter.common.conf import settings as smarter_settings
from smarter.common.utils import is_authenticated_request, smarter_build_absolute_uri
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAdminAPIView,
    SmarterAdminListAPIView,
)
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class AccountViewBase(SmarterAdminAPIView):
    """Base class for account views."""

    serializer_class = AccountSerializer

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code < 300 and isinstance(request.user, User):
            # we now have to consider superuser accounts that are associated with multiple accounts
            self.user_profile = UserProfile.objects.filter(user=request.user).first()
        return response


class AccountListViewBase(SmarterAdminListAPIView):
    """Base class for account list views."""

    serializer_class = AccountSerializer

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        logger.info(
            "%s.dispatch() - request: %s, user: %s",
            self.formatted_class_name,
            request,
            request.user.username if request.user else "Anonymous",  # type: ignore[assignment]
        )
        if response.status_code < 300 and isinstance(request.user, User):
            # we now have to consider superuser accounts that are associated with multiple accounts
            self.user_profile = UserProfile.objects.filter(user=request.user).first()
        return response

    def setup(self, request, *args, **kwargs):
        """Setup the view. This is called by Django before dispatch() and is used to set up the view for the request."""
        super().setup(request, *args, **kwargs)
        if not hasattr(self.request, "user") or not isinstance(self.request.user, User):
            logger.warning(
                "%s.setup() - request has no user or user is not an instance of User: %s",
                self.formatted_class_name,
                self.request.user,
            )
        else:
            if not is_authenticated_request(self.request):
                logger.warning(
                    "%s.setup() - request user is not authenticated: %s",
                    self.formatted_class_name,
                    self.request.user,
                )
        logger.info(
            "%s.setup() - request: %s, user: %s, user_profile: %s is_authenticated: %s",
            self.formatted_class_name,
            smarter_build_absolute_uri(self.request),
            self.request.user.username if self.request.user else "Anonymous",  # type: ignore[assignment]
            self.user_profile,
            is_authenticated_request(self.request),
        )
