# pylint: disable=wrong-import-position
"""Test LLMPrices model."""

from decimal import Decimal

from smarter.apps.account.models import ChargeTypes, LLMPrices
from smarter.apps.account.models.llm_prices import get_cached_price
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.provider.models import Provider
from smarter.lib import logging

logger = logging.getLogger(__name__)


class TestLLMPrices(TestAccountMixin):
    """Test LLMPrices model."""

    logger_prefix = f"{logging.formatted_text(__name__)}.TestLLMPrices()"

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
        """Test that we can do all crud."""
        provider_name = "test-provider" + self.hash_suffix
        model_name = "test-model" + self.hash_suffix
        price = Decimal(1.25125)
        price_precision = 6
        LLMPrices.objects.create(
            charge_type=ChargeTypes.PROMPT_COMPLETION.value,
            provider=provider_name,
            model=model_name,
            price=price,
        )

        try:
            record = LLMPrices.objects.get(
                charge_type=ChargeTypes.PROMPT_COMPLETION.value, provider=provider_name, model=model_name
            )

            self.assertEqual(record.provider, provider_name)
            self.assertEqual(record.charge_type, ChargeTypes.PROMPT_COMPLETION.value)
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

    def test_cost_of_is_cached_and_invalidated(self):
        """A price is cached, and saving or deleting it invalidates the cache."""
        charge_type = ChargeTypes.PROMPT_COMPLETION.value
        model_name = "test-cached-model" + self.hash_suffix
        record = LLMPrices.objects.create(
            charge_type=charge_type, provider="OpenAI", model=model_name, price=Decimal("2")
        )
        self.addCleanup(LLMPrices.objects.filter(model=model_name).delete)
        self.assertEqual(LLMPrices.cost_of(charge_type, "openai", model_name, 1000000), Decimal("2"))

        # a queryset update bypasses save(), so the cached price is still read.
        LLMPrices.objects.filter(pk=record.pk).update(price=Decimal("3"))
        self.assertEqual(get_cached_price(charge_type, "openai", model_name), Decimal("2"))

        record.price = Decimal("4")
        record.save()
        self.assertEqual(LLMPrices.cost_of(charge_type, "OPENAI", model_name, 1000000), Decimal("4"))

        record.delete()
        self.assertEqual(LLMPrices.cost_of(charge_type, "openai", model_name, 1000000), Decimal("0"))
