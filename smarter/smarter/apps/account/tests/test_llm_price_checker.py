"""
Test :mod:`smarter.apps.account.llm_price_checker`, the Smarter LLM Price Checker.

The pricing page is a trimmed copy of a real provider's page, ``data/llm_price_checker/``, which
the code under test fetches with ``safe_http.fetch`` patched. The LLMClient's prompt is patched
too, so no LLM is called: each test answers as the checker would, and the checks of its answer are
tested on what it may and may not change.
"""

import contextlib
import os
from decimal import Decimal
from unittest.mock import MagicMock, patch

from waffle.testutils import override_switch

from smarter.apps.account import llm_price_checker
from smarter.apps.account.llm_price_catalog import SEEDED_CHARGE_TYPES, blend
from smarter.apps.account.llm_price_checker import (
    LLMPriceCheckerCurrentPrice,
    LLMPriceCheckerPrice,
    LLMPriceCheckerRequest,
    apply_price,
    blended,
    check_llm_prices,
    check_page,
    check_price,
    checked_prices,
    dollar_amounts,
    page_markdown,
    parse_answer,
)
from smarter.apps.account.models import LLMPrices, LLMPriceSource
from smarter.apps.llmclient.prompting import SmarterLLMClientPromptError
from smarter.apps.llmtool.plugin.safe_http import SafeHttpError, SafeResponse
from smarter.apps.prompt.contract.models import (
    PromptChatApiMessage,
    PromptChatApiPromptResult,
)
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.unittest.base_classes import SmarterTestBase

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE_PATH = os.path.join(HERE, "data", "llm_price_checker", "anthropic-pricing.html")
PAGE_URL = "https://platform.claude.com/docs/en/about-claude/pricing"
CHECKER = SmarterWaffleSwitches.ENABLE_LLM_PRICE_CHECKER

with open(PAGE_PATH, "rb") as page_file:
    PAGE_HTML = page_file.read()


def answer_text(text: str) -> PromptChatApiPromptResult:
    """A prompt's result, whose assistant answered with a text."""
    return PromptChatApiPromptResult(status=200, messages=[PromptChatApiMessage(role="assistant", content=text)])


def answer(*prices: dict) -> PromptChatApiPromptResult:
    """A prompt's result, whose assistant answered with prices."""
    text = json.dumps({"prices": list(prices)})
    return answer_text(text)


def page_response(url: str = PAGE_URL, **kwargs) -> SafeResponse:
    """The pricing page, as ``safe_http.fetch`` returns it."""
    return SafeResponse(
        url=url, status_code=200, headers={"content-type": "text/html; charset=utf-8"}, content=PAGE_HTML
    )


class TestLLMPriceChecker(SmarterTestBase):
    """The checker reads a pricing page, and only the prices that pass the checks are applied."""

    def setUp(self):
        super().setUp()
        # a provider of its own, so that the test changes no price that another test could see.
        self.provider = f"test_provider_{self.hash_suffix}"
        self.addCleanup(LLMPrices.objects.filter(provider=self.provider).delete)

    def create_prices(
        self,
        model: str = "claude-sonnet-4-6",
        input_price: str = "2.50",
        output_price: str = "12.50",
        source: str = LLMPriceSource.CATALOG,
        source_url: str = PAGE_URL,
    ) -> None:
        """Price a model of the test's provider for each charge type, as the catalog does."""
        for charge_type in SEEDED_CHARGE_TYPES:
            LLMPrices.objects.create(
                charge_type=charge_type,
                provider=self.provider,
                model=model,
                price=blend(Decimal(input_price), Decimal(output_price)),
                input_price=Decimal(input_price),
                output_price=Decimal(output_price),
                source=source,
                source_url=source_url,
            )

    def price(self, model: str = "claude-sonnet-4-6", **kwargs) -> dict:
        """The checker's answer for a model of the test's provider."""
        price = {
            "provider": self.provider,
            "model": model,
            "found": True,
            "input": "3",
            "output": "15",
            "evidence": "Claude Sonnet 4.6 | $3 / MTok | $15 / MTok",
        }
        price.update(kwargs)
        return price

    def request(self, page: str = "") -> LLMPriceCheckerRequest:
        """A request for the test's model."""
        models = [LLMPriceCheckerCurrentPrice(provider=self.provider, model="claude-sonnet-4-6")]
        return LLMPriceCheckerRequest(url=PAGE_URL, models=models, page=page)

    def rows(self, model: str = "claude-sonnet-4-6"):
        """The prices of a model of the test's provider."""
        return LLMPrices.objects.filter(provider=self.provider, model=model)

    def page_models(self) -> list[LLMPriceCheckerCurrentPrice]:
        """The test provider's models of the pricing page, as the checker finds them."""
        found = []
        for current in checked_prices()[PAGE_URL]:
            if current.provider == self.provider:
                found.append(current)
        return found

    @contextlib.contextmanager
    def llm(self, *results):
        """Serve the pricing page, and answer the checker's prompts with results, in order."""
        with (
            patch.object(llm_price_checker.safe_http, "fetch", side_effect=page_response) as fetch,
            patch.object(llm_price_checker, "prompt_in_process", side_effect=list(results)) as prompt,
        ):
            yield fetch, prompt

    # the page
    # ---------------------------------------------------------------------------------------------

    def test_page_markdown_keeps_the_table(self):
        """The page's table becomes a Markdown table, whose row has the model's prices."""
        with patch.object(llm_price_checker.safe_http, "fetch", side_effect=page_response):
            page = page_markdown(PAGE_URL)
        self.assertIn("Claude Sonnet 4.6", page)
        rows = []
        for line in page.splitlines():
            if "Claude Sonnet 4.6" in line and "|" in line:
                rows.append(line)
        self.assertEqual(len(rows), 1)
        self.assertIn("$3", rows[0])
        self.assertIn("$15", rows[0])
        self.assertNotIn("<table", page)

    def test_page_markdown_without_text(self):
        empty = SafeResponse(url=PAGE_URL, status_code=200, headers={}, content=b"<html><body></body></html>")
        with patch.object(llm_price_checker.safe_http, "fetch", return_value=empty):
            with self.assertRaises(SmarterValueError):
                page_markdown(PAGE_URL)

    def test_dollar_amounts(self):
        amounts = dollar_amounts("$3 / MTok, $0.30, $ 15.00 and $1,250.50, but not 7 or USD 9.")
        self.assertEqual(amounts, {Decimal("3"), Decimal("0.30"), Decimal("15"), Decimal("1250.50")})
        self.assertIn(Decimal("3.00"), amounts)

    def test_dollar_amounts_of_the_page(self):
        with patch.object(llm_price_checker.safe_http, "fetch", side_effect=page_response):
            page = page_markdown(PAGE_URL)
        amounts = dollar_amounts(page)
        for amount in ("3", "15", "1.50", "7.50"):
            self.assertIn(Decimal(amount), amounts)

    def test_blended_is_rounded_to_the_column(self):
        self.assertEqual(blended(Decimal("3"), Decimal("15")), Decimal("6.000000"))
        self.assertEqual(blended(Decimal("0.0000001"), Decimal("0")), Decimal("0.000000"))

    # the answer
    # ---------------------------------------------------------------------------------------------

    def test_parse_answer(self):
        text = "```json\n" + json.dumps({"prices": [self.price()], "note": "extra"}) + "\n```"
        parsed = parse_answer(text)
        self.assertEqual(parsed.prices[0].input, Decimal("3"))

    def test_parse_answer_refuses(self):
        for text in (None, "", "no json here", '{"prices": "none"}'):
            with self.subTest(text=text):
                with self.assertRaises(SmarterValueError):
                    parse_answer(text)

    # the checks
    # ---------------------------------------------------------------------------------------------

    def test_check_price(self):
        """Each way that a price can be wrong is refused, and a price on the page is accepted."""
        self.create_prices()
        request = self.request()
        amounts = {Decimal("3"), Decimal("15"), Decimal("0"), Decimal("40"), Decimal("200")}
        cases = {
            "isn't a model": self.price(model="claude-unknown"),
            "didn't find": self.price(found=False),
            "no input or output": self.price(output=None),
            "negative": self.price(input="-3"),
            "both prices are zero": self.price(input="0", output="0"),
            "$7 isn't written": self.price(input="7"),
            "$16 isn't written": self.price(output="16"),
            "more than 3 times": self.price(input="40", output="200"),
        }
        for reason, price in cases.items():
            with self.subTest(reason=reason):
                refusal = check_price(LLMPriceCheckerPrice.model_validate(price), request, amounts)
                self.assertIsNotNone(refusal)
                self.assertIn(reason, str(refusal))
        accepted = check_price(LLMPriceCheckerPrice.model_validate(self.price()), request, amounts)
        self.assertIsNone(accepted)

    def test_check_price_refuses_a_large_drop(self):
        self.create_prices(input_price="30", output_price="150")
        price = LLMPriceCheckerPrice.model_validate(self.price())
        refusal = check_price(price, self.request(), {Decimal("3"), Decimal("15")})
        self.assertIn("divided by 3", str(refusal))

    def test_check_price_of_a_model_without_a_price(self):
        """A model that has no price yet has nothing to compare to."""
        price = LLMPriceCheckerPrice.model_validate(self.price())
        refusal = check_price(price, self.request(), {Decimal("3"), Decimal("15")})
        self.assertIsNone(refusal)

    # the prices
    # ---------------------------------------------------------------------------------------------

    def test_checked_prices(self):
        """Each model of a page once, and never a person's price, or one without a page."""
        self.create_prices()
        self.create_prices(model="claude-haiku-4-5", source=LLMPriceSource.LLM)
        self.create_prices(model="claude-person", source=LLMPriceSource.HUMAN)
        self.create_prices(model="claude-no-page", source_url="")
        models = [current.model for current in self.page_models()]
        self.assertEqual(models, ["claude-haiku-4-5", "claude-sonnet-4-6"])

    def test_apply_price_leaves_a_persons_price(self):
        self.create_prices()
        person = self.rows()[0]
        LLMPrices.objects.filter(pk=person.pk).update(source=LLMPriceSource.HUMAN, price=Decimal("9"))
        changed = apply_price(LLMPriceCheckerPrice.model_validate(self.price()))
        self.assertTrue(changed)
        person.refresh_from_db()
        self.assertEqual(person.price, Decimal("9"))
        self.assertIsNone(person.checked_at)
        others = self.rows().exclude(pk=person.pk)
        self.assertEqual(set(others.values_list("price", flat=True)), {Decimal("6")})

    def test_apply_price_invalidates_the_cached_price(self):
        """A charge is priced at the new price as soon as it is applied."""
        self.create_prices()
        charge_type = SEEDED_CHARGE_TYPES[0]
        before = LLMPrices.cost_of(charge_type, self.provider, "claude-sonnet-4-6", 1_000_000)
        apply_price(LLMPriceCheckerPrice.model_validate(self.price()))
        after = LLMPrices.cost_of(charge_type, self.provider, "claude-sonnet-4-6", 1_000_000)
        self.assertEqual(before, Decimal("5"))
        self.assertEqual(after, Decimal("6"))

    # a page, end to end
    # ---------------------------------------------------------------------------------------------

    def test_check_page_changes_the_price(self):
        """The provider's new price, on the page, is applied to every charge type, as the checker's."""
        self.create_prices()
        with self.llm(answer(self.price())) as (fetch, prompt):
            result = check_page(MagicMock(), PAGE_URL, self.page_models())
        fetch.assert_called_once()
        request = json.loads(prompt.call_args.args[1])
        self.assertIn("Claude Sonnet 4.6", request["page"])
        self.assertEqual(request["models"][0]["input"], "2.500000")
        self.assertEqual(result.changed, 1)
        self.assertEqual(result.checked, 1)
        self.assertEqual(result.refused, [])
        for row in self.rows():
            self.assertEqual(row.price, Decimal("6"))
            self.assertEqual(row.input_price, Decimal("3"))
            self.assertEqual(row.output_price, Decimal("15"))
            self.assertEqual(row.source, LLMPriceSource.LLM)
            self.assertIsNotNone(row.checked_at)

    def test_check_page_confirms_the_price(self):
        """An unchanged price is only marked as checked, and stays the catalog's."""
        self.create_prices(input_price="3", output_price="15")
        with self.llm(answer(self.price())):
            result = check_page(MagicMock(), PAGE_URL, self.page_models())
        self.assertEqual(result.changed, 0)
        self.assertEqual(result.checked, 1)
        for row in self.rows():
            self.assertEqual(row.source, LLMPriceSource.CATALOG)
            self.assertIsNotNone(row.checked_at)

    def test_check_page_refuses_a_batch_price(self):
        """The batch price is written on the page, but is too far from the current price, and is refused."""
        self.create_prices(input_price="3", output_price="15")
        LLMPrices.objects.filter(provider=self.provider).update(price=Decimal("20"))
        with self.llm(answer(self.price(input="1.50", output="7.50"))):
            result = check_page(MagicMock(), PAGE_URL, self.page_models())
        self.assertEqual(result.checked, 0)
        self.assertEqual(len(result.refused), 1)
        self.assertEqual(set(self.rows().values_list("price", flat=True)), {Decimal("20")})

    def test_check_page_refuses_an_invented_price(self):
        self.create_prices()
        with self.llm(answer(self.price(input="3.10"))):
            result = check_page(MagicMock(), PAGE_URL, self.page_models())
        self.assertIn("$3.10 isn't written on the page", result.refused[0])
        self.assertEqual(set(self.rows().values_list("source", flat=True)), {LLMPriceSource.CATALOG})

    def test_check_page_without_the_page(self):
        self.create_prices()
        with (
            patch.object(llm_price_checker.safe_http, "fetch", side_effect=SafeHttpError("HTTP 503")),
            patch.object(llm_price_checker, "prompt_in_process") as prompt,
        ):
            result = check_page(MagicMock(), PAGE_URL, self.page_models())
        prompt.assert_not_called()
        self.assertIn("HTTP 503", result.error)

    def test_check_page_when_the_llm_fails(self):
        self.create_prices()
        for failure in (SmarterLLMClientPromptError("budget exceeded"), answer_text("I can't read this page.")):
            with self.subTest(failure=type(failure).__name__):
                with self.llm(failure):
                    result = check_page(MagicMock(), PAGE_URL, self.page_models())
                self.assertNotEqual(result.error, "")
                self.assertEqual(result.checked, 0)

    # every page
    # ---------------------------------------------------------------------------------------------

    def test_check_llm_prices(self):
        self.create_prices()
        pages = {PAGE_URL: self.page_models()}
        with (
            override_switch(CHECKER, active=True),
            patch.object(llm_price_checker, "smarter_llmclient", return_value=MagicMock()),
            patch.object(llm_price_checker, "checked_prices", return_value=pages),
            self.llm(answer(self.price())),
        ):
            results = check_llm_prices()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].changed, 1)

    def test_check_llm_prices_when_off(self):
        with (
            override_switch(CHECKER, active=False),
            patch.object(llm_price_checker, "smarter_llmclient") as find,
        ):
            self.assertEqual(check_llm_prices(), [])
        find.assert_not_called()

    def test_check_llm_prices_without_the_llmclient(self):
        with (
            override_switch(CHECKER, active=True),
            patch.object(llm_price_checker, "smarter_llmclient", return_value=None),
            patch.object(llm_price_checker, "check_page") as check,
        ):
            self.assertEqual(check_llm_prices(), [])
        check.assert_not_called()
