# pylint: disable=W0707,W0718
"""Account views for smarter api."""
import logging

from django.shortcuts import get_object_or_404

from smarter.apps.account.models import User, UserProfile
from smarter.apps.account.serializers import AccountSerializer
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAdminAPIView,
    SmarterAdminListAPIView,
)
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class AccountViewBase(SmarterAdminAPIView):
    """Base class for account views."""

    serializer_class = AccountSerializer

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code < 300 and isinstance(request.user, User):
            self.user_profile = get_object_or_404(UserProfile, user=request.user)
        return response


class AccountListViewBase(SmarterAdminListAPIView):
    """Base class for account list views."""

    serializer_class = AccountSerializer

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code < 300 and isinstance(request.user, User):
            self.user_profile = get_object_or_404(UserProfile, user=request.user)
        return response
