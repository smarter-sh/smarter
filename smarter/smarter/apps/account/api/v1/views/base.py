# pylint: disable=W0707,W0718
"""Account views for smarter api."""
import logging

from django.shortcuts import get_object_or_404

from smarter.apps.account.models import UserProfile
from smarter.apps.account.serializers import AccountSerializer
from smarter.lib.django.user import UserClass as User
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAdminAPIView,
    SmarterAdminListAPIView,
)


logger = logging.getLogger(__name__)


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
