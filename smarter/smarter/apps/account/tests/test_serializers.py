"""Unit test base classes for Smarter."""

import logging

from smarter.common.helpers.console_helpers import formatted_text

from ..models import PaymentMethod, Secret
from ..serializers import (
    AccountMiniSerializer,
    AccountSerializer,
    PaymentMethodSerializer,
    SecretSerializer,
    UserProfileSerializer,
)
from .factories import (
    factory_secret_teardown,
    payment_method_factory,
    payment_method_factory_teardown,
    secret_factory,
)
from .mixins import TestAccountMixin


logger = logging.getLogger(__name__)


class TestSerializers(TestAccountMixin):
    """Test serializers for the account app."""

    secret: Secret = None
    payment_method: PaymentMethod = None
    test_serializers_logger_prefix = formatted_text(f"{__name__}.TestSerializers()")

    @classmethod
    def setUpClass(cls):
        """Set up test data for the test case."""
        super().setUpClass()
        logger.debug("%s.setUpClass()", cls.test_serializers_logger_prefix)
        cls.secret = secret_factory(user_profile=cls.user_profile, name=cls.name, description="test", value="test")
        cls.payment_method = payment_method_factory(cls.account)

    @classmethod
    def tearDownClass(cls):
        """Tear down test data after the test case."""
        logger.debug("%s.tearDownClass()", cls.test_serializers_logger_prefix)
        try:
            factory_secret_teardown(secret=cls.secret)
            cls.secret = None
            payment_method_factory_teardown(payment_method=cls.payment_method)
            cls.payment_method = None
        # pylint: disable=W0718
        except Exception:
            pass
        finally:
            super().tearDownClass()

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

    def test_payment_method_serializer(self):
        """Test the PaymentMethodSerializer."""
        serializer = PaymentMethodSerializer(self.payment_method)
        data = serializer.data
        self.assertIsInstance(data, dict)

    def test_secret_serializer(self):
        """Test the SecretSerializer."""
        serializer = SecretSerializer(self.secret)
        data = serializer.data
        self.assertIsInstance(data, dict)
