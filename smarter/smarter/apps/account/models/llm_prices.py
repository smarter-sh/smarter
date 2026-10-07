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

# django stuff
from django.db import models

# our stuff
from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


class LLMPrices(TimestampedModel):
    """
    LLMPrices model for managing markup factors in account billing.

    Stores provider/model-specific price markups, enabling proportional billing across all accounts based on their usage.

    :param charge_type: String. The type of charge (e.g., completion, plugin, tool).
    :param provider: String. The LLM provider (e.g., OpenAI, Meta AI).
    :param model: String. The model name.
    :param price: Decimal. The price in USD per million tokens, markup included. :meth:`cost_of` uses it to price charges, which budgets that measure cost compare to their limits.

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

    # pylint: disable=C0115
    class Meta:
        unique_together = ("charge_type", "provider", "model")

    def __str__(self):
        return f"{self.charge_type} - {self.provider} - {self.model} - {self.price}"

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
        price = (
            cls.objects.filter(charge_type=charge_type, provider__iexact=provider, model=model)
            .values_list("price", flat=True)
            .first()
        )
        if price is None:
            return Decimal("0")
        return (Decimal(total_tokens) * price / Decimal(1000000)).quantize(Decimal("0.00000001"))


__all__ = ["LLMPrices"]
