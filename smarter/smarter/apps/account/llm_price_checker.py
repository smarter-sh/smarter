"""
The Smarter LLM Price Checker: an LLMClient that keeps the LLM prices up to date, every week.

Every :class:`~smarter.apps.account.models.LLMPrices` row that the price catalog or the checker
itself set, and that has a ``source_url``, is checked against that page: the provider's pricing
page. The platform fetches each page once, converts it to Markdown, and prompts the staff-only
LLMClient ``smarter_llm_price_checker`` of the Smarter account with the page and the models that it
prices. The LLMClient answers with each model's standard price per million input and output
tokens, as JSON.

Its answer is checked again here, whatever its system prompt says (:func:`check_price`):

- a price must be of a model that it was asked about;
- its input and output prices must both be dollar amounts that are written on the page, so that it
  can't invent a number;
- the new blended price may differ from the current one by a factor of at most
  :data:`~smarter.apps.account.const.LLM_PRICE_CHECKER_MAX_CHANGE`, up or down. A larger change is
  more likely a misreading, e.g. of a batch rate or of another model's row, than a new price.

A price that fails is refused, logged, and kept as it was. A price that a person set
(:attr:`~smarter.apps.account.models.LLMPriceSource.HUMAN`), e.g. in the Django admin, is never
checked or changed. Celery Beat runs :func:`smarter.apps.account.tasks.check_llm_prices` every week,
while the ``enable_llm_price_checker`` switch is on.

The LLMClient is prompted in-process, as its owner, with
:func:`smarter.apps.llmclient.prompting.prompt_in_process`: its system prompt, guardrails and
budget apply, as they would to a person's prompt.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from django.utils import timezone
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.prompting import (
    SmarterLLMClientPromptError,
    assistant_text,
    extract_json_object,
    prompt_in_process,
    smarter_llmclient,
)
from smarter.apps.llmtool.plugin import safe_http
from smarter.apps.llmtool.plugin.websearch_fetch import html_to_markdown, truncate
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active
from smarter.lib.typing import required

from .const import (
    LLM_PRICE_CHECKER_LLMCLIENT,
    LLM_PRICE_CHECKER_MAX_CHANGE,
    LLM_PRICE_CHECKER_MAX_PAGE_CHARACTERS,
)
from .llm_price_catalog import blend
from .models import LLMPrices, LLMPriceSource

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])

CHECKED_SOURCES = (LLMPriceSource.CATALOG, LLMPriceSource.LLM)
"""The sources of the prices that the checker keeps up to date.

A person's are never changed.
"""

USER_AGENT = "smarter-llm-price-checker"
"""The user agent of the checker's ``Prompt`` sessions, which no browser opened."""

MAX_PAGE_BYTES = 5_000_000
"""The largest pricing page, in bytes, that is fetched.

Providers' pages are under a megabyte.
"""

PRICE_PLACES = Decimal("0.000001")
"""The precision of :attr:`LLMPrices.price`: six decimal places."""

DOLLAR_AMOUNT = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?")
"""A dollar amount written on a page, e.g. ``$0.05``, ``$3`` or ``$1,250.00``."""


class LLMPriceCheckerModel(BaseModel):
    """The base class of the checker's request and answer: snake_case JSON."""

    model_config = ConfigDict(extra="forbid")


class LLMPriceCheckerCurrentPrice(LLMPriceCheckerModel):
    """A model whose price the checker is asked for, with the price that the platform has now."""

    provider: str
    model: str
    input: Optional[Decimal] = Field(default=None, description="USD per million input tokens, if known.")
    output: Optional[Decimal] = Field(default=None, description="USD per million output tokens, if known.")


class LLMPriceCheckerRequest(LLMPriceCheckerModel):
    """The checker's prompt: a pricing page, and the models that it prices."""

    url: str = Field(description="The page's url.")
    models: list[LLMPriceCheckerCurrentPrice]
    page: str = Field(description="The page, as Markdown.")

    def current(self, provider: str, model: str) -> Optional[LLMPriceCheckerCurrentPrice]:
        """
        Return a model of the request.

        :param provider: The provider's name.
        :param model: The model's name.
        :returns: The model, or ``None`` if the request doesn't have it.
        :rtype: Optional[LLMPriceCheckerCurrentPrice]
        """
        for candidate in self.models:
            if candidate.provider != provider:
                continue
            if candidate.model != model:
                continue
            return candidate
        return None


class LLMPriceCheckerPrice(BaseModel):
    """
    The checker's price of one model.

    Extra fields are ignored: an LLM adds some.
    """

    model_config = ConfigDict(extra="ignore")

    provider: str
    model: str
    found: bool = Field(description="Whether the page has the model's standard price.")
    input: Optional[Decimal] = None
    output: Optional[Decimal] = None
    evidence: str = Field(default="", description="The page's words that give the price.")


class LLMPriceCheckerAnswer(BaseModel):
    """The checker's answer."""

    model_config = ConfigDict(extra="ignore")

    prices: list[LLMPriceCheckerPrice]


class LLMPriceCheckerResult(BaseModel):
    """What the checker did with one pricing page."""

    model_config = ConfigDict(extra="forbid")

    url: str
    checked: int = Field(default=0, description="The models whose price was confirmed or changed.")
    changed: int = Field(default=0, description="The models whose price changed.")
    refused: list[str] = Field(default_factory=list, description="Why each refused price was refused.")
    error: str = Field(default="", description="Why the page couldn't be checked at all.")


def blended(input_price: Decimal, output_price: Decimal) -> Decimal:
    """
    Return the price that a model's input and output prices are stored at, as the catalog blends them.

    :param input_price: USD per million input tokens.
    :param output_price: USD per million output tokens.
    :returns: USD per million tokens, :func:`~smarter.apps.account.llm_price_catalog.blend`, rounded
        to the six decimal places that :attr:`LLMPrices.price` stores.
    :rtype: Decimal
    """
    price = blend(input_price, output_price)
    rounded = price.quantize(PRICE_PLACES)
    return rounded


def checked_prices() -> dict[str, list[LLMPriceCheckerCurrentPrice]]:
    """
    Return the models whose prices the checker keeps up to date, by the page that publishes them.

    :returns: For each pricing page, its models, each once, whatever its charge types.
    :rtype: dict[str, list[LLMPriceCheckerCurrentPrice]]
    """
    rows = LLMPrices.objects.filter(source__in=CHECKED_SOURCES).exclude(source_url="").order_by("provider", "model")
    pages: dict[str, list[LLMPriceCheckerCurrentPrice]] = {}
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (row.source_url, row.provider, row.model)
        if key in seen:
            continue
        seen.add(key)
        current = LLMPriceCheckerCurrentPrice(
            provider=row.provider, model=row.model, input=row.input_price, output=row.output_price
        )
        pages.setdefault(row.source_url, []).append(current)
    return pages


def page_markdown(url: str) -> str:
    """
    Fetch a pricing page, and return it as Markdown, whose tables keep their rows and columns.

    :param url: The page's url.
    :returns: The page's main content, at most
        :data:`~smarter.apps.account.const.LLM_PRICE_CHECKER_MAX_PAGE_CHARACTERS` characters.
    :rtype: str
    :raises safe_http.SafeHttpError: If the page can't be fetched.
    :raises SmarterValueError: If the page has no text.
    """
    response = safe_http.fetch(url, max_bytes=MAX_PAGE_BYTES)
    _, markdown = html_to_markdown(response.content, response.url, response.charset)
    if not markdown:
        raise SmarterValueError(f"The page {url} has no text.")
    page, _ = truncate(markdown, LLM_PRICE_CHECKER_MAX_PAGE_CHARACTERS)
    return page


def dollar_amounts(page: str) -> set[Decimal]:
    """
    Return the dollar amounts that are written on a page.

    :param page: The page's text.
    :returns: Each amount, e.g. ``Decimal("0.05")`` for ``$0.05``. ``$3`` and ``$3.00`` are equal.
    :rtype: set[Decimal]
    """
    amounts = set()
    for match in DOLLAR_AMOUNT.finditer(page):
        whole = match.group(1).replace(",", "")
        fraction = match.group(2) or ""
        try:
            amount = Decimal(whole + fraction)
        except InvalidOperation:
            continue
        amounts.add(amount)
    return amounts


def parse_answer(text: Optional[str]) -> LLMPriceCheckerAnswer:
    """
    Parse the checker's answer.

    :param text: The answer, which should be one JSON object, perhaps in a code fence.
    :returns: The prices.
    :rtype: LLMPriceCheckerAnswer
    :raises SmarterValueError: If it isn't a valid answer.
    """
    if not text:
        raise SmarterValueError("The checker gave no answer.")
    data = extract_json_object(text)
    if data is None:
        raise SmarterValueError("The checker's answer has no JSON object.")
    try:
        answer = LLMPriceCheckerAnswer.model_validate(data)
    except ValidationError as e:
        raise SmarterValueError(f"The checker's answer isn't valid: {e}") from e
    return answer


def current_price(provider: str, model: str) -> Optional[Decimal]:
    """
    Return the price that the platform has now for a model, of any charge type that the checker keeps.

    :param provider: The provider's name.
    :param model: The model's name.
    :returns: USD per million tokens, or ``None`` if the model has no such price.
    :rtype: Optional[Decimal]
    """
    rows = LLMPrices.objects.filter(provider=provider, model=model, source__in=CHECKED_SOURCES)
    price = rows.values_list("price", flat=True).first()
    return price


def check_price(price: LLMPriceCheckerPrice, request: LLMPriceCheckerRequest, amounts: set[Decimal]) -> Optional[str]:
    """
    Check a price that the checker read, against its request and its page.

    :param price: The checker's price of a model.
    :param request: The request that it answers.
    :param amounts: The dollar amounts written on the page, from :func:`dollar_amounts`.
    :returns: Why the price is refused, or ``None`` if it is fine.
    :rtype: Optional[str]
    """
    if request.current(price.provider, price.model) is None:
        return "it isn't a model that the checker was asked about"
    if not price.found:
        return "the checker didn't find its standard price on the page"
    if price.input is None or price.output is None:
        return "the checker gave no input or output price"
    if price.input < 0 or price.output < 0:
        return "a price is negative"
    if price.input == 0 and price.output == 0:
        return "both prices are zero"
    if price.input not in amounts:
        return f"${price.input} isn't written on the page"
    if price.output not in amounts:
        return f"${price.output} isn't written on the page"
    new = blended(price.input, price.output)
    refusal = check_change(price.provider, price.model, new)
    return refusal


def check_change(provider: str, model: str, new: Decimal) -> Optional[str]:
    """
    Check that a model's new price is within a factor of its current price, up or down.

    :param provider: The provider's name.
    :param model: The model's name.
    :param new: The new blended price, in USD per million tokens.
    :returns: Why the change is refused, or ``None`` if it is fine, or the model has no price yet.
    :rtype: Optional[str]
    """
    current = current_price(provider, model)
    if current is None or current <= 0:
        return None
    if new > current * LLM_PRICE_CHECKER_MAX_CHANGE:
        return f"${new} is more than {LLM_PRICE_CHECKER_MAX_CHANGE} times the current ${current}"
    if new * LLM_PRICE_CHECKER_MAX_CHANGE < current:
        return f"${new} is less than the current ${current} divided by {LLM_PRICE_CHECKER_MAX_CHANGE}"
    return None


def apply_price(price: LLMPriceCheckerPrice) -> bool:
    """
    Apply a checked price to every charge type's row of its model that the checker keeps.

    A row whose price is unchanged is only marked as checked, and keeps its source.

    :param price: The price, which :func:`check_price` accepted.
    :returns: True if the price changed.
    :rtype: bool
    """
    input_price = required(price.input, "input")
    output_price = required(price.output, "output")
    new = blended(input_price, output_price)
    now = timezone.now()
    changed = False
    rows = LLMPrices.objects.filter(provider=price.provider, model=price.model, source__in=CHECKED_SOURCES)
    for row in rows:
        old = row.price
        row.checked_at = now
        if old == new and row.input_price == input_price and row.output_price == output_price:
            row.save()
            continue
        row.price = new
        row.input_price = input_price
        row.output_price = output_price
        row.source = LLMPriceSource.LLM
        row.save()
        changed = True
        logger.info(
            "changed the %s price of %s %s from $%s to $%s per million tokens.",
            row.charge_type,
            row.provider,
            row.model,
            old,
            new,
        )
    return changed


def session_url() -> str:
    """
    Return the url that the checker's ``Prompt`` sessions come from: the platform's.

    :returns: The url.
    :rtype: str
    """
    url = f"{smarter_settings.environment_url}/"
    return url


def check_page(llmclient: LLMClient, url: str, models: list[LLMPriceCheckerCurrentPrice]) -> LLMPriceCheckerResult:
    """
    Ask the checker for the prices of a page's models, and apply those that pass the checks.

    :param llmclient: The checker.
    :param url: The pricing page.
    :param models: Its models, with their current prices.
    :returns: What was checked, changed and refused.
    :rtype: LLMPriceCheckerResult
    """
    result = LLMPriceCheckerResult(url=url)
    try:
        page = page_markdown(url)
    except SmarterValueError as e:
        result.error = str(e)
        logger.warning("couldn't read the pricing page %s, so its prices are kept: %s", url, e)
        return result

    request = LLMPriceCheckerRequest(url=url, models=models, page=page)
    request_json = request.model_dump(mode="json")
    try:
        prompt_result = prompt_in_process(llmclient, json.dumps(request_json), session_url(), USER_AGENT)
        text = assistant_text(prompt_result)
        answer = parse_answer(text)
    except (SmarterLLMClientPromptError, SmarterValueError) as e:
        result.error = str(e)
        logger.warning("the checker failed for %s, so its prices are kept: %s", url, e)
        return result

    amounts = dollar_amounts(page)
    for price in answer.prices:
        refusal = check_price(price, request, amounts)
        if refusal is not None:
            result.refused.append(f"{price.provider} {price.model}: {refusal}")
            continue
        if apply_price(price):
            result.changed += 1
        result.checked += 1
    for refusal in result.refused:
        logger.warning("refused a price from %s: %s", url, refusal)
    return result


def check_llm_prices() -> list[LLMPriceCheckerResult]:
    """
    Check every price that the checker keeps, page by page, while the ``enable_llm_price_checker`` switch is on.

    :returns: What was done with each pricing page, or nothing if the switch is off or the checker
        doesn't exist on this platform.
    :rtype: list[LLMPriceCheckerResult]
    """
    if not switch_is_active(SmarterWaffleSwitches.ENABLE_LLM_PRICE_CHECKER):
        return []
    llmclient = smarter_llmclient(LLM_PRICE_CHECKER_LLMCLIENT)
    if llmclient is None:
        logger.info(
            "the LLMClient %s doesn't exist, so the LLM prices aren't checked.",
            LLM_PRICE_CHECKER_LLMCLIENT,
        )
        return []
    results = []
    for url, models in checked_prices().items():
        result = check_page(llmclient, url, models)
        results.append(result)
    return results


__all__ = [
    "LLMPriceCheckerAnswer",
    "LLMPriceCheckerPrice",
    "LLMPriceCheckerRequest",
    "LLMPriceCheckerResult",
    "apply_price",
    "check_llm_prices",
    "check_change",
    "check_page",
    "check_price",
    "checked_prices",
    "dollar_amounts",
    "page_markdown",
    "parse_answer",
]
