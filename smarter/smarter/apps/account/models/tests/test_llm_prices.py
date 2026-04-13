# pylint: disable=wrong-import-position
"""Test LLMPrices model."""

# our stuff
import logging

from smarter.apps.account.models import CHARGE_TYPES, LLMPrices
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.provider.models import Provider
from smarter.common.helpers.console_helpers import formatted_text

logger = logging.getLogger(__name__)


class TestLLMPrices(TestAccountMixin):
    """Test LLMPrices model"""

    logger_prefix = formatted_text(f"{__name__}.TestLLMPrices()")

    @classmethod
    def setUpClass(cls):
        cls.provider = Provider.objects.create(name="Test Provider", slug="test-provider")
        super().setUpClass()
        logger.debug("%s Created provider: %s", cls.logger_prefix, cls.provider)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.provider.delete()
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("%s Error deleting provider: %s", cls.logger_prefix, e)

        super().tearDownClass()
        logger.debug("%s Tear down complete.", cls.logger_prefix)

    def test_crud(self):
        """
        Test that we can do all crud.

        """

        LLMPrices.objects.create(
            charge_type=CHARGE_TYPES[0][0],
            provider="test-provider",
            model="test-model",
            price=1.25125,
        )

        record = LLMPrices.objects.get(charge_type=CHARGE_TYPES[0][0], provider="test-provider", model="test-model")

        self.assertEqual(record.provider, "test-provider")
        self.assertEqual(record.charge_type, CHARGE_TYPES[0][0])
        self.assertEqual(record.model, "test-model")
        self.assertEqual(record.price, 1.25125)

        record.price = 2.5025
        record.save()

        self.assertEqual(record.price, 2.5025)

        record.delete()
