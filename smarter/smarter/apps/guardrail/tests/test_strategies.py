"""
Test the guardrail strategies: :mod:`smarter.apps.guardrail.services.strategies`.

The scored strategies use :class:`.base_classes.FakeGuardrailClient` instead of an LLM provider.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.core.cache import cache

from smarter.apps.guardrail.models import Guardrail
from smarter.apps.guardrail.services.exceptions import (
    GuardrailConfigError,
    GuardrailProviderError,
    GuardrailStrategyNotImplementedError,
)
from smarter.apps.guardrail.services.strategies.base import StrategyContext
from smarter.apps.guardrail.services.strategies.clients import parse_verdict
from smarter.apps.guardrail.services.strategies.registry import (
    get_client,
    get_strategy,
)
from smarter.apps.guardrail.services.strategies.semantic_strategy import (
    cosine_similarity,
    embedding_cache_key,
)
from smarter.apps.provider.services.text_completion.contracts import (
    GuardrailStage,
    TextSegment,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import FakeGuardrailClient, fake_client

CONTEXT = StrategyContext(stage=GuardrailStage.PRE)


def guardrail(strategy: str, pattern=None, threshold=None, **config) -> Guardrail:
    """Return an unsaved Guardrail with a strategy and its config."""
    return Guardrail(name=f"test_{strategy}", strategy=strategy, pattern=pattern, threshold=threshold, config=config)


def evaluate(g: Guardrail, text: str):
    """Evaluate a Guardrail's strategy on a text."""
    return get_strategy(g.strategy).evaluate(segment=TextSegment(path="p", text=text), guardrail=g, context=CONTEXT)


class TestGuardrailStrategies(SmarterTestBase):
    """Test each strategy, and the registry."""

    # -------------------------------------------------------------------------
    # regex
    # -------------------------------------------------------------------------
    def test_regex(self):
        """Test that the regex strategy finds every match, case insensitively by default."""
        match = evaluate(guardrail("regex", pattern=r"drop\s+table"), "DROP TABLE a; drop  table b")
        self.assertTrue(match.triggered)
        self.assertEqual(match.confidence, 1.0)
        self.assertEqual([m.text for m in match.matches], ["DROP TABLE", "drop  table"])
        self.assertFalse(evaluate(guardrail("regex", pattern="xyz"), "abc").triggered)

    def test_regex_flags(self):
        """Test that explicit flags replace the default IGNORECASE."""
        self.assertFalse(evaluate(guardrail("regex", pattern="abc", flags=[]), "ABC").triggered)
        self.assertTrue(evaluate(guardrail("regex", pattern="^b", flags=["MULTILINE"]), "a\nb").triggered)

    def test_regex_misconfigured(self):
        """Test that a regex guardrail without a valid pattern raises, rather than silently passing."""
        with self.assertRaises(GuardrailConfigError):
            evaluate(guardrail("regex"), "text")
        with self.assertRaises(GuardrailConfigError):
            evaluate(guardrail("regex", pattern="([unclosed"), "text")
        with self.assertRaises(GuardrailConfigError):
            evaluate(guardrail("regex", pattern="x", flags=["VERBOSE"]), "text")

    # -------------------------------------------------------------------------
    # keyword
    # -------------------------------------------------------------------------
    def test_keyword(self):
        """Test that the keyword strategy matches whole words and phrases, across whitespace, case insensitively."""
        g = guardrail("keyword", keywords=["ignore previous instructions", "DAN"])
        match = evaluate(g, "Please IGNORE previous\ninstructions, dan.")
        self.assertEqual([m.label for m in match.matches], ["ignore previous\ninstructions", "dan"])
        self.assertFalse(evaluate(g, "the dance was fun").triggered)

    def test_keyword_options(self):
        """Test caseSensitive and wholeWord."""
        self.assertFalse(evaluate(guardrail("keyword", keywords=["DAN"], caseSensitive=True), "dan").triggered)
        self.assertTrue(evaluate(guardrail("keyword", keywords=["dan"], wholeWord=False), "dance").triggered)

    def test_keyword_misconfigured(self):
        """Test that a keyword guardrail without keywords raises."""
        with self.assertRaises(GuardrailConfigError):
            evaluate(guardrail("keyword", keywords=[" "]), "text")

    # -------------------------------------------------------------------------
    # detector
    # -------------------------------------------------------------------------
    def test_detector(self):
        """Test that the detector strategy reports what it detected."""
        match = evaluate(guardrail("detector", detectors=["email", "us_ssn"]), "mail a@b.io ssn 123-45-6789")
        self.assertEqual([m.label for m in match.matches], ["email", "us_ssn"])
        self.assertIn("email", match.rationale)
        self.assertFalse(evaluate(guardrail("detector", detectors=["email"]), "no email").triggered)

    def test_detector_misconfigured(self):
        """Test that a detector guardrail without detectors, or with unknown ones, raises."""
        with self.assertRaises(GuardrailConfigError):
            evaluate(guardrail("detector"), "text")
        with self.assertRaises(GuardrailConfigError):
            evaluate(guardrail("detector", detectors=["passport"]), "text")

    # -------------------------------------------------------------------------
    # semantic
    # -------------------------------------------------------------------------
    def test_semantic(self):
        """Test that the semantic strategy triggers on similarity to a reference text."""
        g = guardrail("semantic", threshold=0.9, referenceTexts=["a forbidden example", "another forbidden thing"])
        cache.delete_many([embedding_cache_key("text-embedding-3-small", t) for t in g.settings["referenceTexts"]])
        with fake_client() as client:
            match = evaluate(g, "this is forbidden")
            self.assertTrue(match.triggered)
            self.assertAlmostEqual(match.confidence, 1.0)
            self.assertFalse(evaluate(g, "this is fine").triggered)
        # the reference texts were embedded once, and then cached
        embedded = [text for name, texts in client.calls if name == "embed" for text in texts]
        self.assertEqual(embedded.count("a forbidden example"), 1)

    def test_semantic_misconfigured(self):
        """Test that a semantic guardrail without reference texts raises."""
        with fake_client(), self.assertRaises(GuardrailConfigError):
            evaluate(guardrail("semantic"), "text")

    def test_cosine_similarity(self):
        """Test cosine_similarity."""
        self.assertAlmostEqual(cosine_similarity([1, 0], [1, 0]), 1.0)
        self.assertAlmostEqual(cosine_similarity([1, 0], [0, 1]), 0.0)
        self.assertEqual(cosine_similarity([0, 0], [1, 0]), 0.0)
        with self.assertRaises(GuardrailProviderError):
            cosine_similarity([1, 0], [1, 0, 0])

    # -------------------------------------------------------------------------
    # moderation
    # -------------------------------------------------------------------------
    def test_moderation(self):
        """Test that the moderation strategy triggers when a selected category reaches the threshold."""
        with fake_client():
            match = evaluate(guardrail("moderation", threshold=0.5, categories=["violence"]), "forbidden")
            self.assertTrue(match.triggered)
            self.assertAlmostEqual(match.confidence, 0.9)
            self.assertIn("violence", match.rationale)
            # hate scores 0.1, below the threshold
            self.assertFalse(
                evaluate(guardrail("moderation", threshold=0.5, categories=["hate"]), "forbidden").triggered
            )
            # without categories, every category counts
            self.assertTrue(evaluate(guardrail("moderation", threshold=0.5), "forbidden").triggered)
            self.assertFalse(evaluate(guardrail("moderation", threshold=0.5), "fine").triggered)

    # -------------------------------------------------------------------------
    # llm_judge
    # -------------------------------------------------------------------------
    def test_llm_judge(self):
        """Test that the llm_judge strategy renders its prompt, and triggers on the judge's verdict."""
        g = guardrail("llm_judge", threshold=0.8, judgePrompt='Judge: """{text}""" {{"json": true}}')
        with fake_client() as client:
            match = evaluate(g, "a forbidden request")
            self.assertTrue(match.triggered)
            self.assertEqual(client.calls[-1], ("judge", 'Judge: """a forbidden request""" {"json": true}'))
            self.assertFalse(evaluate(g, "a fine request").triggered)

    def test_llm_judge_threshold(self):
        """Test that a verdict below the threshold does not trigger."""
        g = guardrail("llm_judge", threshold=0.99, judgePrompt="{text}")
        with fake_client(FakeGuardrailClient(judge_confidence=0.9)):
            self.assertFalse(evaluate(g, "forbidden").triggered)

    def test_llm_judge_text_with_braces(self):
        """Test that braces in the judged text are not interpreted as placeholders."""
        g = guardrail("llm_judge", judgePrompt="Judge: {text}")
        with fake_client():
            self.assertFalse(evaluate(g, "{user} {0} {text}").triggered)

    def test_llm_judge_misconfigured(self):
        """Test that an llm_judge guardrail without {text} in its prompt raises."""
        with fake_client(), self.assertRaises(GuardrailConfigError):
            evaluate(guardrail("llm_judge", judgePrompt="Judge this."), "text")

    def test_parse_verdict(self):
        """Test the parsing of a judge's JSON reply."""
        verdict = parse_verdict('{"triggered": true, "confidence": 0.9, "rationale": "why"}')
        self.assertEqual((verdict.triggered, verdict.confidence, verdict.rationale), (True, 0.9, "why"))
        self.assertEqual(parse_verdict('{"triggered": "false"}').confidence, 0.0)
        self.assertEqual(parse_verdict('{"triggered": true, "confidence": 7}').confidence, 1.0)
        for reply in ("not json", "[]", '{"confidence": 1}', None):
            with self.subTest(reply=reply), self.assertRaises(GuardrailProviderError):
                parse_verdict(reply)

    # -------------------------------------------------------------------------
    # registry
    # -------------------------------------------------------------------------
    def test_registry(self):
        """Test that each strategy is registered, and an unknown one raises."""
        for strategy in ("regex", "keyword", "detector", "semantic", "moderation", "llm_judge"):
            self.assertIsNotNone(get_strategy(strategy))
        with self.assertRaises(GuardrailStrategyNotImplementedError):
            get_strategy("model")

    def test_configure_clients(self):
        """Test that configure_clients installs a client factory, and that None restores the default."""
        g = guardrail("moderation")
        with fake_client() as client:
            self.assertIs(get_client(g), client)
        with self.assertRaises(GuardrailConfigError):
            # the default client needs the Guardrail's owner to read an LLM provider
            get_client(g)

    def test_provider_failure(self):
        """Test that a failing provider call raises GuardrailProviderError."""
        with fake_client(FakeGuardrailClient(fail=True)), self.assertRaises(GuardrailProviderError):
            evaluate(guardrail("moderation"), "text")
