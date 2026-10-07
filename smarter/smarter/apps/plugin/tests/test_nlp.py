# pylint: disable=wrong-import-position
"""
Test :mod:`smarter.apps.plugin.nlp`.

Plugin selectors use these functions to decide whether a prompt refers to one
of their search terms. The test cases are in ./data/nlp.yaml.
"""

from unittest import mock

from smarter.apps.plugin.nlp import (
    allowed_distance,
    clean_prompt,
    does_refer_to,
    lower_case_splitter,
    normalized_words,
    simple_search,
    within_levenshtein_distance,
    word_matches,
)
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import get_test_data

logger = logging.getLogger(__name__)

SWITCH_PATCH = "smarter.apps.plugin.nlp.switch_is_active"


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
        with mock.patch(SWITCH_PATCH, return_value=False) as switch_is_active:
            self.assertFalse(does_refer_to(prompt, search_term))
        switch_is_active.assert_called_once_with(SmarterWaffleSwitches.ENABLE_PLUGIN_FUZZY_MATCHING)
        with mock.patch(SWITCH_PATCH, return_value=True):
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
