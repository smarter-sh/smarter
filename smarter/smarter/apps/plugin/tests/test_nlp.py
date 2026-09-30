# pylint: disable=wrong-import-position
"""
Test :mod:`smarter.apps.plugin.nlp`, which plugin selectors use to decide.

whether a prompt refers to one of their search terms.

The test cases are in ./data/nlp.yaml.
"""

from smarter.apps.plugin.nlp import (
    clean_prompt,
    does_refer_to,
    lower_case_splitter,
    simple_search,
    within_levenshtein_distance,
)
from smarter.lib import logging
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import get_test_data

logger = logging.getLogger(__name__)


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

    def test_simple_search(self):
        """Test that simple_search() matches the search term, or all of its words, case insensitively."""
        for case in self.cases["simple_search"]:
            with self.subTest(prompt=case["prompt"], search_term=case["search_term"]):
                self.assertEqual(simple_search(case["prompt"], case["search_term"]), case["expected"])

    def test_within_levenshtein_distance(self):
        """Test within_levenshtein_distance().

        See the note in ./data/nlp.yaml.
        """
        for case in self.cases["within_levenshtein_distance"]:
            with self.subTest(prompt=case["prompt"], search_term=case["search_term"]):
                self.assertEqual(
                    within_levenshtein_distance(case["prompt"], case["search_term"], threshold=case["threshold"]),
                    case["expected"],
                )

    def test_does_refer_to(self):
        """Test that does_refer_to() cleans the prompt, and then searches it."""
        for case in self.cases["does_refer_to"]:
            with self.subTest(prompt=case["prompt"], search_term=case["search_term"]):
                self.assertEqual(does_refer_to(case["prompt"], case["search_term"]), case["expected"])
