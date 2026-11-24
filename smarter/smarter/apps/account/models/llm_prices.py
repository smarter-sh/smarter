"""
Account LLMPrices Model
=======================

This module defines the :class:`LLMPrices` model for managing provider/model-specific markup factors
used in account billing. It enables proportional billing across all accounts based on their usage
of different LLM providers and models.

Classes
-------

- :class:`LLMPrices`: Stores markup prices for each (charge_type, provider, model) combination.

Key Features
------------

- Tracks markup factors for each provider/model/charge type.
- Enforces uniqueness for (charge_type, provider, model) combinations.
- Supports flexible billing and cost allocation for LLM usage.

Example
-------

.. code-block:: python

    from smarter.apps.account.models import LLMPrices

    markup = LLMPrices.objects.get(provider="openai", model="gpt-4").price
    account_charge = provider_cost * markup * account_usage_ratio
"""

from decimal import Decimal
from typing import Optional

from cache_results import cache_results

# django stuff
from django.db import models

# our stuff
from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


@cache_results()
def get_cached_price(charge_type: str, provider: str, model: str) -> Optional[Decimal]:
    """
    Return the price, in USD per million tokens, of a charge type, provider and model, or None.

    Every charge is priced, so the price is cached. :class:`LLMPrices` invalidates it when
    a price is saved or deleted.

    :param charge_type: The charge type.
    :type charge_type: str
    :param provider: The provider's name, lowercased, since providers match case-insensitively.
    :type provider: str
    :param model: The model's name.
    :type model: str
    :returns: The price, or None if there is none.
    :rtype: Optional[Decimal]
    """
    return (
        LLMPrices.objects.filter(charge_type=charge_type, provider__iexact=provider, model=model)
        .values_list("price", flat=True)
        .first()
    )


class LLMPriceSource(models.TextChoices):
    """
    Who set an :class:`LLMPrices` row's price.

    The Smarter LLM Price Checker, :mod:`smarter.apps.account.llm_price_checker`, keeps the prices
    of the catalog and its own up to date, and never changes a person's.
    """

    CATALOG = "catalog", "Price catalog"
    """``manage.py initialize_llm_prices`` created it, from the price catalog ``data/llm_prices.yaml``."""

    LLM = "llm", "Smarter LLM Price Checker"
    """The Smarter LLM Price Checker read it on its source's page."""

    HUMAN = "human", "A person"
    """A person set it, e.g. in the Django admin.

    It is never changed automatically.
    """


class LLMPrices(TimestampedModel):
    """
    LLMPrices model for managing markup factors in account billing.

    Stores provider/model-specific price markups, enabling proportional billing across all accounts based on their usage.

    :param charge_type: String. The type of charge (e.g., completion, plugin, tool).
    :param provider: String. The LLM provider (e.g., OpenAI, Meta AI).
    :param model: String. The model name.
    :param price: Decimal. The price in USD per million tokens, markup included. :meth:`cost_of` uses it to price charges, which budgets that measure cost compare to their limits.
    :param source: String. Who set the price, an :class:`LLMPriceSource`. A row created any other way than by the catalog or the Smarter LLM Price Checker is a person's.
    :param source_url: String. The provider's page that publishes the model's price, which the Smarter LLM Price Checker reads every week.
    :param input_price: Decimal, optional. The provider's price per million input tokens.
    :param output_price: Decimal, optional. The provider's price per million output tokens.
    :param checked_at: Datetime, optional. When the price was last checked against its source.

    .. note::

        Markup factors are used to calculate each account's share of provider costs.

    **Example usage**::

        # Calculate account charge for provider/model usage
        markup = LLMPrices.objects.get(provider="openai", model="gpt-4").price
        account_charge = provider_cost * markup * account_usage_ratio

    :TODO: create a Choice or FK to charge_type field.
    :TODO: create some form of referential integrity for model and provider fields.
    :TODO: establish reasonable boundaries on price field.

    .. seealso::

        :class:`Account`, :class:`Charge`
    """

    charge_type = models.CharField(max_length=20)
    provider = models.CharField(max_length=255)
    model = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=6)
    source = models.CharField(
        max_length=20,
        choices=LLMPriceSource.choices,
        default=LLMPriceSource.HUMAN,
        help_text="Who set the price. The Smarter LLM Price Checker never changes a price that a person set.",
    )
    source_url = models.URLField(
        max_length=2048,
        blank=True,
        default="",
        help_text="The provider's page that publishes the model's price. The Smarter LLM Price Checker reads it.",
    )
    input_price = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="The provider's price, in USD per million input tokens, that the price was blended from.",
    )
    output_price = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="The provider's price, in USD per million output tokens, that the price was blended from.",
    )
    checked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the price was last checked against its source.",
    )

    # pylint: disable=C0115
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["charge_type", "provider", "model"], name="account_llmprices_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.charge_type} - {self.provider} - {self.model} - {self.price}"

    def save(self, *args, **kwargs):
        """Save the price, and invalidate its cached value."""
        super().save(*args, **kwargs)
        get_cached_price.invalidate(self.charge_type, self.provider.lower(), self.model)  # type: ignore[attr-defined]

    def delete(self, *args, **kwargs):
        """Delete the price, and invalidate its cached value."""
        retval = super().delete(*args, **kwargs)
        get_cached_price.invalidate(self.charge_type, self.provider.lower(), self.model)  # type: ignore[attr-defined]
        return retval

    @classmethod
    def cost_of(
        cls, charge_type: Optional[str], provider: Optional[str], model: Optional[str], total_tokens: int
    ) -> Decimal:
        """
        The cost in USD of total_tokens, where price is USD per million tokens.

        Budgets that measure cost use it. Without a price for the charge type, provider and
        model, the cost is 0.
        """
        if not (charge_type and provider and model and total_tokens):
            return Decimal("0")
        price = get_cached_price(charge_type, provider.lower(), model)
        if price is None:
            return Decimal("0")
        return (Decimal(total_tokens) * price / Decimal(1000000)).quantize(Decimal("0.00000001"))


__all__ = ["LLMPriceSource", "LLMPrices"]
