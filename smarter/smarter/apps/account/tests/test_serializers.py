"""Unit test base classes for Smarter."""

import logging

from smarter.common.helpers.console_helpers import formatted_text

from ..serializers import (
    AccountMiniSerializer,
    AccountSerializer,
    UserProfileSerializer,
)
from .mixins import TestAccountMixin

logger = logging.getLogger(__name__)


class TestSerializers(TestAccountMixin):
    """Test serializers for the account app."""

    test_serializers_logger_prefix = formatted_text(f"{__name__}.TestSerializers()")

    def test_account_serializer(self):
        """Test the AccountSerializer."""
        serializer = AccountSerializer(self.account)
        data = serializer.data
        self.assertIsInstance(data, dict)

    def test_account_mini_serializer(self):
        """Test the AccountMiniSerializer."""
        serializer = AccountMiniSerializer(self.account)
        data = serializer.data
        self.assertIsInstance(data, dict)

    def test_user_profile_serializer(self):
        """Test the UserProfileSerializer."""
        serializer = UserProfileSerializer(self.user_profile)
        data = serializer.data
        self.assertIsInstance(data, dict)
