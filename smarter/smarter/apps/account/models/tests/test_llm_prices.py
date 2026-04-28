# pylint: disable=wrong-import-position
"""Test LLMPrices model."""

import logging

# our stuff
from decimal import Decimal

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
        super().setUpClass()
        cls.provider = Provider.objects.create(name="Test Provider", user_profile=cls.user_profile)
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
        provider_name = "test-provider" + self.hash_suffix
        model_name = "test-model" + self.hash_suffix
        price = Decimal(1.25125)
        price_precision = 6
        LLMPrices.objects.create(
            charge_type=CHARGE_TYPES[0][0],
            provider=provider_name,
            model=model_name,
            price=price,
        )

        try:
            record = LLMPrices.objects.get(charge_type=CHARGE_TYPES[0][0], provider=provider_name, model=model_name)

            self.assertEqual(record.provider, provider_name)
            self.assertEqual(record.charge_type, CHARGE_TYPES[0][0])
            self.assertEqual(record.model, model_name)
            self.assertEqual(round(record.price, price_precision), round(price, price_precision))

            price = Decimal(1.75375)

            record.price = price
            record.save()

            self.assertEqual(round(record.price, price_precision), round(price, price_precision))
        # pylint: disable=broad-except
        except Exception as e:
            self.fail(f"Error during CRUD operations: {e}")
        finally:
            try:
                record.delete()
            # pylint: disable=broad-except
            except Exception as e:
                logger.error("%s Error deleting record: %s", self.logger_prefix, e)
