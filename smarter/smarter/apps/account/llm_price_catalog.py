"""
The price catalog: the LLM prices that a new platform starts with, ``data/llm_prices.yaml``.

Each entry is a model's price as its provider publishes it, in USD per million input tokens and per
million output tokens, with the page that published it. An :class:`~smarter.apps.account.models.LLMPrices`
row has one price per million tokens, which a charge's total tokens are multiplied by, so each entry
is stored at its blended price, :func:`blended_price`.

``manage.py initialize_llm_prices``, which ``initialize_platform`` runs, calls :func:`seed_llm_prices`.
The catalog only starts a platform's prices: they live in the database, where the Smarter LLM Price
Checker, :mod:`smarter.apps.account.llm_price_checker`, keeps them up to date every week, and a
person may change them in the Django admin.
"""

import datetime
from decimal import Decimal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .const import LLM_PRICES_PATH
from .models import ChargeTypes, LLMPrices, LLMPriceSource

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])

INPUT_TOKENS_PER_OUTPUT_TOKEN = 3
"""
The mix of tokens that a blended price assumes: three input tokens to one output token.

It is the industry's usual convention for a single price per token. An application whose prompts
are long and whose answers are short, e.g. one with tools and a large system prompt, uses more
input tokens than that, so its blended price slightly overstates its cost.
"""

SEEDED_CHARGE_TYPES = (
    ChargeTypes.PROMPT_COMPLETION.value,
    ChargeTypes.PLUGIN.value,
    ChargeTypes.TOOL.value,
)
"""The charge types that each model is priced for: a model call, and the plugin and tool calls that it makes."""


class LLMPriceCatalogEntry(BaseModel):
    """A model's price, as its provider publishes it."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1, max_length=255, description="The provider's name, e.g. openai.")
    model: str = Field(min_length=1, max_length=255, description="The model's name, e.g. gpt-6-luna.")
    input: Decimal = Field(ge=0, description="USD per million input tokens.")
    output: Decimal = Field(ge=0, description="USD per million output tokens.")
    source: str = Field(min_length=1, description="The page that published the price.")
    checked: datetime.date = Field(description="The day that the price was checked on that page.")


class LLMPriceCatalog(BaseModel):
    """The catalog file, ``data/llm_prices.yaml``."""

    model_config = ConfigDict(extra="forbid")

    prices: list[LLMPriceCatalogEntry] = Field(description="The models' prices.")


def blend(input_price: Decimal, output_price: Decimal) -> Decimal:
    """
    Return the single price per million tokens of an input and an output price.

    :param input_price: USD per million input tokens.
    :param output_price: USD per million output tokens.
    :returns: USD per million tokens, (3 * input + output) / 4.
    :rtype: Decimal
    """
    input_cost = input_price * INPUT_TOKENS_PER_OUTPUT_TOKEN
    total_cost = input_cost + output_price
    tokens = INPUT_TOKENS_PER_OUTPUT_TOKEN + 1
    price = total_cost / tokens
    return price


def blended_price(entry: LLMPriceCatalogEntry) -> Decimal:
    """
    Return a model's single price per million tokens, of three input tokens to one output token.

    :param entry: The model's price.
    :returns: USD per million tokens, (3 * input + output) / 4. See :func:`blend`.
    :rtype: Decimal
    """
    price = blend(entry.input, entry.output)
    return price


def load_llm_price_catalog(path: str = LLM_PRICES_PATH) -> LLMPriceCatalog:
    """
    Read and validate the price catalog.

    :param path: The catalog's file.
    :returns: The catalog.
    :rtype: LLMPriceCatalog
    :raises pydantic.ValidationError: If the file isn't a valid catalog.
    :raises OSError: If the file can't be read.
    """
    with open(path, encoding="utf-8") as catalog_file:
        data = yaml.safe_load(catalog_file)
    catalog = LLMPriceCatalog.model_validate(data)
    return catalog


def checked_at(entry: LLMPriceCatalogEntry) -> datetime.datetime:
    """
    Return when a catalog entry's price was checked, as a datetime: midnight UTC of its ``checked`` day.

    :param entry: The model's price.
    :returns: The datetime.
    :rtype: datetime.datetime
    """
    midnight = datetime.time(0, 0, tzinfo=datetime.timezone.utc)
    when = datetime.datetime.combine(entry.checked, midnight)
    return when


def adopt(row: LLMPrices, entry: LLMPriceCatalogEntry, price: Decimal) -> bool:
    """
    Mark an existing price as the catalog's, when it is exactly the catalog's price and has no source.

    A price that was created before prices recorded their source is a person's, by default. When it
    is still the catalog's blended price, the catalog created it, so it becomes the catalog's again,
    and the Smarter LLM Price Checker keeps it up to date. Any other price stays a person's.

    :param row: The existing price.
    :param entry: The catalog's price of its model.
    :param price: The entry's blended price.
    :returns: True if the row was adopted.
    :rtype: bool
    """
    if row.source != LLMPriceSource.HUMAN:
        return False
    if row.source_url:
        return False
    if row.price != price:
        return False
    row.source = LLMPriceSource.CATALOG
    row.source_url = entry.source
    row.input_price = entry.input
    row.output_price = entry.output
    row.checked_at = checked_at(entry)
    row.save()
    return True


def seed_llm_prices(catalog: LLMPriceCatalog) -> tuple[int, int]:
    """
    Create the catalog's prices that don't exist yet, for each charge type, and keep those that do.

    A price that exists, e.g. one that a person changed in the Django admin, is never changed. An
    existing price that is still exactly the catalog's, with no source, is marked as the catalog's
    (:func:`adopt`), so that the Smarter LLM Price Checker keeps it up to date.

    :param catalog: The catalog.
    :returns: The number of prices created, and the number that already existed.
    :rtype: tuple[int, int]
    """
    created = 0
    kept = 0
    adopted = 0
    for entry in catalog.prices:
        price = blended_price(entry)
        for charge_type in SEEDED_CHARGE_TYPES:
            row, was_created = LLMPrices.objects.get_or_create(
                charge_type=charge_type,
                provider=entry.provider,
                model=entry.model,
                defaults={
                    "price": price,
                    "source": LLMPriceSource.CATALOG,
                    "source_url": entry.source,
                    "input_price": entry.input,
                    "output_price": entry.output,
                    "checked_at": checked_at(entry),
                },
            )
            if was_created:
                created += 1
                continue
            kept += 1
            if adopt(row, entry, price):
                adopted += 1
    logger.info(
        "created %s llm prices, and kept %s that already existed, of which %s are the catalog's again.",
        created,
        kept,
        adopted,
    )
    return created, kept
