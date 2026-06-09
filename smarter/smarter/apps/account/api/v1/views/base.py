# pylint: disable=W0707,W0718
"""Account views for smarter api."""

from smarter.apps.account.serializers import AccountSerializer
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAdminAPIView,
    SmarterAdminListAPIView,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


class AccountViewBase(SmarterAdminAPIView):
    """Base class for account views."""

    serializer_class = AccountSerializer


class AccountListViewBase(SmarterAdminListAPIView):
    """Base class for account list views."""

    serializer_class = AccountSerializer
