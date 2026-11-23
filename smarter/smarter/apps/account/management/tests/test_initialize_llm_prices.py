"""Test the initialize_llm_prices management command, and the price catalog that it reads."""

import os
import tempfile
from decimal import Decimal

import yaml

from smarter.apps.account.llm_price_catalog import (
    SEEDED_CHARGE_TYPES,
    LLMPriceCatalogEntry,
    blended_price,
    load_llm_price_catalog,
)
from smarter.apps.account.models import ChargeTypes, LLMPrices

from .base import CommandTestBase


class TestInitializeLLMPrices(CommandTestBase):
    """Test that the catalog's missing prices are created, for each charge type, and existing ones kept."""

    def setUp(self):
        super().setUp()
        # a provider of its own, so that the test creates no price that another test could see.
        self.provider = self.unique("test_provider")
        self.addCleanup(LLMPrices.objects.filter(provider=self.provider).delete)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

    def catalog_file(self, prices: list[dict]) -> str:
        """Write a catalog to a temporary file, and return its path."""
        path = os.path.join(self.folder.name, "llm_prices.yaml")
        with open(path, "w", encoding="utf-8") as catalog_file:
            yaml.safe_dump({"prices": prices}, catalog_file)
        return path

    def entry(self, model: str = "test-model", input_price: str = "0.10", output_price: str = "0.50") -> dict:
        """A catalog entry of the test's provider."""
        return {
            "provider": self.provider,
            "model": model,
            "input": input_price,
            "output": output_price,
            "source": "https://example.com/pricing",
            "checked": "2026-11-23",
        }

    def test_blended_price(self):
        """Three input tokens to one output token: $0.10 in and $0.50 out is $0.20 per million tokens."""
        entry = LLMPriceCatalogEntry.model_validate(self.entry())
        self.assertEqual(blended_price(entry), Decimal("0.20"))

    def test_creates_each_charge_type(self):
        """Each model is priced for completion, plugin and tool charges, at its blended price."""
        output = self.run_command("initialize_llm_prices", file=self.catalog_file([self.entry()]))
        self.assertIn("Created 3 LLM prices, and kept 0", output)
        prices = LLMPrices.objects.filter(provider=self.provider, model="test-model")
        self.assertEqual(set(prices.values_list("charge_type", flat=True)), set(SEEDED_CHARGE_TYPES))
        for price in prices:
            self.assertEqual(price.price, Decimal("0.20"))
        cost = LLMPrices.cost_of(ChargeTypes.PROMPT_COMPLETION.value, self.provider.upper(), "test-model", 1_000_000)
        self.assertEqual(cost, Decimal("0.20"))

    def test_keeps_existing_prices(self):
        """Running it again creates nothing, and an operator's price is never changed."""
        path = self.catalog_file([self.entry()])
        self.run_command("initialize_llm_prices", file=path)
        LLMPrices.objects.filter(provider=self.provider, charge_type=ChargeTypes.PROMPT_COMPLETION.value).update(
            price=Decimal("9.99")
        )
        output = self.run_command("initialize_llm_prices", file=path)
        self.assertIn("Created 0 LLM prices, and kept 3", output)
        completion = LLMPrices.objects.get(provider=self.provider, charge_type=ChargeTypes.PROMPT_COMPLETION.value)
        self.assertEqual(completion.price, Decimal("9.99"))

    def test_an_invalid_catalog_fails(self):
        """A catalog with a negative price, or an unknown field, fails, and creates nothing."""
        bad_prices = [self.entry(input_price="-1")]
        with self.assertRaises(SystemExit):
            self.run_command("initialize_llm_prices", file=self.catalog_file(bad_prices))
        unknown_field = [{**self.entry(), "currency": "EUR"}]
        with self.assertRaises(SystemExit):
            self.run_command("initialize_llm_prices", file=self.catalog_file(unknown_field))
        self.assertFalse(LLMPrices.objects.filter(provider=self.provider).exists())

    def test_the_platforms_catalog_is_valid(self):
        """The catalog that platforms start with is valid, and each of its entries has a source."""
        catalog = load_llm_price_catalog()
        self.assertTrue(catalog.prices)
        for entry in catalog.prices:
            with self.subTest(model=entry.model):
                self.assertTrue(entry.source.startswith("https://"))
                self.assertGreater(blended_price(entry), 0)
