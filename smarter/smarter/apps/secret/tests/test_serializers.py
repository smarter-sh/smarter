"""Smarter Secret app serializers tests."""

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.secret.models import Secret
from smarter.apps.secret.serializers import SecretSerializer
from smarter.lib import logging

from .factories import (
    factory_secret_teardown,
    secret_factory,
)

logger = logging.getSmarterLogger(__name__)


class TestSerializers(TestAccountMixin):
    """Test serializers for the account app."""

    secret: Secret

    @classmethod
    def setUpClass(cls):
        """Set up test data for the test case."""
        super().setUpClass()
        logger.debug("called.")
        cls.secret = secret_factory(user_profile=cls.user_profile, name=cls.name, description="test", value="test")

    @classmethod
    def tearDownClass(cls):
        """Tear down test data after the test case."""
        logger.debug("called.")
        try:
            factory_secret_teardown(secret=cls.secret)
        # pylint: disable=W0718
        except Exception:
            pass
        finally:
            super().tearDownClass()

    def test_secret_serializer(self):
        """Test the SecretSerializer."""
        serializer = SecretSerializer(self.secret)
        data = serializer.data
        self.assertIsInstance(data, dict)
