# pylint: disable=wrong-import-position
"""
Test :mod:`smarter.apps.plugin.nlp`.

Plugin selectors use these functions to decide whether a prompt refers to one
of their search terms. The test cases are in ./data/nlp.yaml. The thesaurus cases
use the real WordNet corpus, which the Docker image installs, and are skipped if
it is not installed.
"""

import unittest
from unittest import mock

from waffle.testutils import override_switch

from smarter.apps.plugin.nlp import (
    MatchMethod,
    allowed_distance,
    clean_prompt,
    contains_phrase,
    does_refer_to,
    lower_case_splitter,
    normalized_words,
    simple_search,
    synonyms,
    thesaurus_match,
    within_levenshtein_distance,
    word_matches,
    wordnet,
)
from smarter.apps.plugin.signals import search_term_matched
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches, smarter_waffle_switches
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import get_test_data

logger = logging.getLogger(__name__)

SWITCH_PATCH = "smarter.apps.plugin.nlp.switch_is_active"
WORDNET_PATCH = "smarter.apps.plugin.nlp.wordnet"
WORDNET_INSTALLED = wordnet() is not None


def switches(fuzzy: bool = False, thesaurus: bool = False):
    """Return a stand-in for switch_is_active, with the fuzzy and thesaurus matching switches on or off."""
    values = {
        SmarterWaffleSwitches.ENABLE_PLUGIN_FUZZY_MATCHING: fuzzy,
        SmarterWaffleSwitches.ENABLE_PLUGIN_THESAURUS_MATCHING: thesaurus,
    }
    return lambda switch_name: values[switch_name]


class TestPluginNlp(SmarterTestBase):
    """Test the nlp functions, with the cases in ./data/nlp.yaml."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = get_test_data("nlp.yaml")

    def test_clean_prompt(self):
        """Test that clean_prompt() separates camel cased words, and removes punctuation."""
        for case in self.cases["clean_prompt"]:
            with self.subTest(prompt=case["prompt"]):
                self.assertEqual(clean_prompt(case["prompt"]), case["expected"])

    def test_lower_case_splitter(self):
        """Test that lower_case_splitter() returns the lower cased words."""
        for case in self.cases["lower_case_splitter"]:
            with self.subTest(value=case["value"]):
                self.assertEqual(lower_case_splitter(case["value"]), case["expected"])

    def test_normalized_words(self):
        """Test that normalized_words() returns the lower cased words, without punctuation."""
        for case in self.cases["normalized_words"]:
            with self.subTest(value=case["value"]):
                self.assertEqual(normalized_words(case["value"]), case["expected"])

    def test_word_matches(self):
        """Test that word_matches() matches equal words and plurals, but not words that contain another."""
        for case in self.cases["word_matches"]:
            with self.subTest(prompt_word=case["prompt_word"], term_word=case["term_word"]):
                self.assertEqual(word_matches(case["prompt_word"], case["term_word"]), case["expected"])

    def test_simple_search(self):
        """Test that simple_search() matches every word of the search term, as whole words."""
        for case in self.cases["simple_search"]:
            with self.subTest(prompt=case["prompt"], search_term=case["search_term"]):
                self.assertEqual(simple_search(case["prompt"], case["search_term"]), case["expected"])

    def test_allowed_distance(self):
        """Test that longer search terms tolerate more typos, and short ones none."""
        for case in self.cases["allowed_distance"]:
            with self.subTest(search_term=case["search_term"]):
                self.assertEqual(allowed_distance(case["search_term"]), case["expected"])

    def test_within_levenshtein_distance(self):
        """Test that within_levenshtein_distance() tolerates typos, without matching unrelated words."""
        for case in self.cases["within_levenshtein_distance"]:
            with self.subTest(prompt=case["prompt"], search_term=case["search_term"]):
                self.assertEqual(
                    within_levenshtein_distance(case["prompt"], case["search_term"], threshold=case.get("threshold")),
                    case["expected"],
                )

    def test_does_refer_to(self):
        """Test that does_refer_to() cleans the prompt, and then searches it, with or without typo tolerance."""
        for case in self.cases["does_refer_to"]:
            with self.subTest(prompt=case["prompt"], search_term=case["search_term"], fuzzy=case["fuzzy"]):
                self.assertEqual(
                    does_refer_to(case["prompt"], case["search_term"], fuzzy=case["fuzzy"]), case["expected"]
                )

    def test_does_refer_to_switch(self):
        """Test that does_refer_to() tolerates typos only if the waffle switch is on."""
        prompt, search_term = "Who is Lawrance McDaniel?", "Lawrence McDaniel"
        with mock.patch(SWITCH_PATCH, side_effect=switches()) as switch_is_active:
            self.assertFalse(does_refer_to(prompt, search_term))
        switch_is_active.assert_any_call(SmarterWaffleSwitches.ENABLE_PLUGIN_FUZZY_MATCHING)
        with mock.patch(SWITCH_PATCH, side_effect=switches(fuzzy=True)):
            self.assertTrue(does_refer_to(prompt, search_term))

    def test_does_refer_to_exact_match_skips_switch(self):
        """Test that an exact match does not check the waffle switch."""
        with mock.patch(SWITCH_PATCH) as switch_is_active:
            self.assertTrue(does_refer_to("Who is Lawrence McDaniel?", "Lawrence McDaniel"))
        switch_is_active.assert_not_called()

    def test_switch_default(self):
        """Test that typo tolerant matching is on by default."""
        switch = SmarterWaffleSwitches.switches[SmarterWaffleSwitches.ENABLE_PLUGIN_FUZZY_MATCHING]
        self.assertTrue(switch.default)

    # -------------------------------------------------------------------------
    # thesaurus
    # -------------------------------------------------------------------------
    @unittest.skipUnless(WORDNET_INSTALLED, "the NLTK WordNet corpus is not installed")
    def test_thesaurus_match(self):
        """Test that thesaurus_match() matches synonyms of common senses, and nothing else."""
        for case in self.cases["thesaurus_match"]:
            with self.subTest(prompt=case["prompt"], search_term=case["search_term"]):
                self.assertEqual(thesaurus_match(case["prompt"], case["search_term"]), case["expected"])

    @unittest.skipUnless(WORDNET_INSTALLED, "the NLTK WordNet corpus is not installed")
    def test_synonyms(self):
        """Test that synonyms() come from the most common senses, and from noun senses for nouns."""
        self.assertIn("automobile", synonyms("car"))
        self.assertNotIn("car", synonyms("car"))
        self.assertNotIn("see", synonyms("image"))
        self.assertIn("monochrome", synonyms("black and white"))
        self.assertIn("weather", synonyms("endure"))
        self.assertEqual(synonyms("endure", nouns_only=True), frozenset())
        self.assertEqual(synonyms("gobstopper"), frozenset())
        self.assertEqual(synonyms(""), frozenset())

    @unittest.skipUnless(WORDNET_INSTALLED, "the NLTK WordNet corpus is not installed")
    def test_does_refer_to_thesaurus_switch(self):
        """Test that does_refer_to() matches synonyms only if use_thesaurus, or else its waffle switch, is on."""
        prompt, search_term = "I want to buy an automobile", "car"
        self.assertTrue(does_refer_to(prompt, search_term, use_thesaurus=True))
        self.assertFalse(does_refer_to(prompt, search_term, use_thesaurus=False))
        with mock.patch(SWITCH_PATCH, side_effect=switches(thesaurus=False)) as switch_is_active:
            self.assertFalse(does_refer_to(prompt, search_term))
        switch_is_active.assert_any_call(SmarterWaffleSwitches.ENABLE_PLUGIN_THESAURUS_MATCHING)
        with mock.patch(SWITCH_PATCH, side_effect=switches(thesaurus=True)):
            self.assertTrue(does_refer_to(prompt, search_term))

    def test_contains_phrase(self):
        """Test that contains_phrase() finds consecutive words, including plurals."""
        words = normalized_words("Compare motor vehicles and bicycles")
        self.assertTrue(contains_phrase(words, "motor vehicle"))
        self.assertTrue(contains_phrase(words, "bicycle"))
        self.assertFalse(contains_phrase(words, "vehicles motor"))
        self.assertFalse(contains_phrase(words, ""))

    def test_wordnet_not_installed(self):
        """Test that, without the WordNet corpus, a warning is logged once, and the thesaurus matches nothing."""
        wordnet.cache_clear()
        self.addCleanup(wordnet.cache_clear)
        self.addCleanup(synonyms.cache_clear)
        with (
            mock.patch("nltk.corpus.wordnet.ensure_loaded", side_effect=LookupError("wordnet")),
            self.assertLogs("smarter.apps.plugin.nlp", level="WARNING") as logs,
        ):
            self.assertIsNone(wordnet())
            self.assertIsNone(wordnet())
        self.assertEqual(len(logs.output), 1)
        self.assertIn("python -m nltk.downloader wordnet", logs.output[0])
        synonyms.cache_clear()
        with mock.patch(WORDNET_PATCH, return_value=None):
            self.assertEqual(synonyms("car"), frozenset())
            self.assertIsNone(thesaurus_match("buy an automobile", "car"))
            self.assertFalse(does_refer_to("buy an automobile", "car", use_thesaurus=True))

    def test_thesaurus_match_with_fake_synonyms(self):
        """Test thesaurus_match() with a fake thesaurus, so that it does not depend on WordNet's contents."""
        fake = {"car": frozenset({"automobile", "motor vehicle"}), "picture": frozenset({"image"})}
        with (
            mock.patch(WORDNET_PATCH, return_value=object()),
            mock.patch(
                "smarter.apps.plugin.nlp.synonyms",
                side_effect=lambda phrase, nouns_only=False: fake.get(phrase, frozenset()),
            ),
        ):
            self.assertEqual(thesaurus_match("sell my automobiles", "car"), "automobile")
            self.assertEqual(thesaurus_match("a garage for motor vehicles", "car"), "motor vehicle")
            self.assertEqual(thesaurus_match("draw a picture", "image"), "picture")
            self.assertEqual(thesaurus_match("a car picture", "car picture"), "car picture")
            self.assertIsNone(thesaurus_match("sell my bicycle", "car"))

    # -------------------------------------------------------------------------
    # search_term_matched signal
    # -------------------------------------------------------------------------
    def capture(self):
        """Collect the kwargs of every search_term_matched signal sent during the test."""
        received = []

        def handler(sender, **kwargs):
            received.append({"sender": sender, **kwargs})

        search_term_matched.connect(handler, weak=False)
        self.addCleanup(search_term_matched.disconnect, handler)
        return received

    def test_signal_exact(self):
        """Test that an exact match sends search_term_matched, with the method exact."""
        received = self.capture()
        self.assertTrue(does_refer_to("WhoIsLawrenceMcDaniel", "Lawrence McDaniel"))
        self.assertEqual(len(received), 1)
        self.assertIs(received[0]["sender"], does_refer_to)
        self.assertEqual(received[0]["prompt"], "WhoIsLawrenceMcDaniel")
        self.assertEqual(received[0]["search_term"], "Lawrence McDaniel")
        self.assertEqual(received[0]["method"], MatchMethod.EXACT)
        self.assertIsNone(received[0]["matched_text"])

    def test_signal_fuzzy(self):
        """Test that a typo tolerant match sends search_term_matched, with the method fuzzy."""
        received = self.capture()
        self.assertTrue(does_refer_to("Who is Lawrance McDaniel?", "Lawrence McDaniel", fuzzy=True))
        self.assertEqual([signal["method"] for signal in received], [MatchMethod.FUZZY])

    def test_signal_thesaurus(self):
        """Test that a thesaurus match sends search_term_matched, with the method thesaurus and the synonym."""
        received = self.capture()
        with mock.patch("smarter.apps.plugin.nlp.thesaurus_match", return_value="automobile"):
            self.assertTrue(does_refer_to("buy an automobile", "car", fuzzy=False, use_thesaurus=True))
        self.assertEqual([signal["method"] for signal in received], [MatchMethod.THESAURUS])
        self.assertEqual(received[0]["matched_text"], "automobile")

    def test_no_signal_without_match(self):
        """Test that no signal is sent when the prompt does not refer to the search term."""
        received = self.capture()
        self.assertFalse(does_refer_to("xyzzy quux", "Lawrence McDaniel", fuzzy=True, use_thesaurus=True))
        self.assertEqual(received, [])

    def test_thesaurus_switch_default(self):
        """Test that thesaurus matching is on by default."""
        switch = SmarterWaffleSwitches.switches[SmarterWaffleSwitches.ENABLE_PLUGIN_THESAURUS_MATCHING]
        self.assertTrue(switch.default)

    def test_thesaurus_switch_is_registered(self):
        """Test that the thesaurus matching switch is registered, so that initialize_waffle creates it."""
        name = SmarterWaffleSwitches.ENABLE_PLUGIN_THESAURUS_MATCHING
        self.assertEqual(name, "enable_plugin_thesaurus_matching")
        self.assertIn(name, smarter_waffle_switches.all)
        switch = SmarterWaffleSwitches.switches[name]
        self.assertEqual(switch.name, name)
        self.assertIn("thesaurus", switch.comment)

    def test_thesaurus_switch_in_database(self):
        """Test that does_refer_to() reads the thesaurus matching switch from the database, through waffle."""
        prompt, search_term = "I want to buy an automobile", "car"
        with mock.patch("smarter.apps.plugin.nlp.thesaurus_match", return_value="automobile") as match:
            with override_switch(SmarterWaffleSwitches.ENABLE_PLUGIN_THESAURUS_MATCHING, active=False):
                self.assertFalse(does_refer_to(prompt, search_term, fuzzy=False))
            match.assert_not_called()
            with override_switch(SmarterWaffleSwitches.ENABLE_PLUGIN_THESAURUS_MATCHING, active=True):
                self.assertTrue(does_refer_to(prompt, search_term, fuzzy=False))
            match.assert_called_once()

    def test_use_thesaurus_overrides_switch(self):
        """Test that an explicit use_thesaurus overrides the thesaurus matching switch."""
        prompt, search_term = "I want to buy an automobile", "car"
        with mock.patch("smarter.apps.plugin.nlp.thesaurus_match", return_value="automobile"):
            with override_switch(SmarterWaffleSwitches.ENABLE_PLUGIN_THESAURUS_MATCHING, active=True):
                self.assertFalse(does_refer_to(prompt, search_term, fuzzy=False, use_thesaurus=False))
            with override_switch(SmarterWaffleSwitches.ENABLE_PLUGIN_THESAURUS_MATCHING, active=False):
                self.assertTrue(does_refer_to(prompt, search_term, fuzzy=False, use_thesaurus=True))
