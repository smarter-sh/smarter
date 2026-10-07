"""Natural language processing functions for OpenAI API-compatible providers."""

import re
import string
from typing import Optional

import Levenshtein

from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

PLURAL_SUFFIXES = ("s", "es")
"""Suffixes with which a prompt's word still matches a search term's word, e.g. Gobstoppers and Gobstopper."""


def clean_prompt(prompt: str) -> str:
    """
    Clean up a prompt by inserting spaces before capital letters.

    This function transforms concatenated or camel-cased words into a more readable format by
    adding spaces before capital letters, except for names starting with "Mc". Useful for
    improving prompt clarity in NLP tasks.

    :param prompt: The input string to clean.
    :type prompt: str

    :return: The cleaned string with spaces before capital letters.
    :rtype: str

    .. note::
        This is a simple heuristic and may not handle all edge cases perfectly.
        For example, names starting with "Mc" (e.g., "McDaniel") are not split.

    .. tip::

        Use this function to preprocess user input or model prompts for better readability.

    .. seealso::

        - :func:`lower_case_splitter`
        - :func:`simple_search`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.nlp import clean_prompt

        s = "WhoIsLawrenceMcDaniel"
        print(clean_prompt(s))
        # Output: "Who Is Lawrence McDaniel"
    """
    pattern = r"(?<!Mc)([A-Z][a-z]+)|(?<!Mc)([A-Z]+)"
    retval = []
    for word in prompt.split():
        word = word.translate(str.maketrans("", "", string.punctuation))
        words = re.sub(pattern, r" \1\2", word).split()
        retval.extend(words)
    retval = " ".join(retval)
    return retval


def lower_case_splitter(string_of_words: str) -> list:
    """
    Split a string on spaces and return a list of lowercase words.

    This function tokenizes a string by spaces and converts each token to lowercase.
    Useful for case-insensitive text processing, search, and normalization in NLP tasks.

    :param string_of_words: The input string to split and lowercase.
    :type string_of_words: str

    :return: List of lowercase words.
    :rtype: list[str]

    .. tip::

        Use this function to prepare text for matching, searching, or comparison.

    .. seealso::

        - :func:`clean_prompt`
        - :func:`normalized_words`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.nlp import lower_case_splitter

        s = "The Quick Brown Fox"
        print(lower_case_splitter(s))
        # Output: ['the', 'quick', 'brown', 'fox']
    """
    return [word.lower() for word in string_of_words.split()]


def normalized_words(text: str) -> list[str]:
    """
    Split a string into lowercase words, without punctuation.

    :param text: The input string.
    :type text: str

    :return: List of lowercase words, from which punctuation is removed.
    :rtype: list[str]

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.nlp import normalized_words

        print(normalized_words("Who is Lawrence P. McDaniel?"))
        # Output: ['who', 'is', 'lawrence', 'p', 'mcdaniel']
    """
    words = [word.translate(str.maketrans("", "", string.punctuation)) for word in lower_case_splitter(text)]
    return [word for word in words if word]


def word_matches(prompt_word: str, term_word: str) -> bool:
    """
    Check if a prompt's word matches a search term's word.

    The words match if they are equal, or if one is the plural of the other, formed
    with one of :data:`PLURAL_SUFFIXES`. Both words are expected to be normalized, as
    by :func:`normalized_words`.

    :param prompt_word: A word of the prompt.
    :type prompt_word: str
    :param term_word: A word of the search term.
    :type term_word: str

    :return: `True` if the words match, otherwise `False`.
    :rtype: bool

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.nlp import word_matches

        print(word_matches("gobstoppers", "gobstopper"))  # True
        print(word_matches("concatenate", "cat"))          # False
    """
    if prompt_word == term_word:
        return True
    return any(prompt_word == term_word + suffix or term_word == prompt_word + suffix for suffix in PLURAL_SUFFIXES)


def simple_search(prompt: str, search_term: str) -> bool:
    """
    Check if the prompt contains every word of the search term.

    This function performs a case-insensitive, whole word search. It returns `True` if
    each word of the `search_term` appears in the `prompt`, in any order, ignoring
    punctuation. A word also matches its plural, e.g. ``Gobstoppers`` matches the
    search term ``Gobstopper``, but it does not match a longer word that merely
    contains it, e.g. ``concatenate`` does not match the search term ``cat``.

    :param prompt: The input string to search within.
    :type prompt: str
    :param search_term: The target string or phrase to look for.
    :type search_term: str

    :return: `True` if the search term is found in the prompt, otherwise `False`. An
        empty search term is never found.
    :rtype: bool

    .. caution::

        This function does not tolerate typos. For typo tolerant matching,
        see :func:`within_levenshtein_distance`.

    .. seealso::

        - :func:`normalized_words`
        - :func:`word_matches`
        - :func:`within_levenshtein_distance`
        - :func:`does_refer_to`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.nlp import simple_search

        prompt = "Find all weather plugins for New York"
        print(simple_search(prompt, "weather plugins"))  # True
        print(simple_search(prompt, "Weather"))          # True
        print(simple_search(prompt, "plugin"))           # True
        print(simple_search(prompt, "California"))       # False
        print(simple_search(prompt, "the"))              # False
    """
    term_words = normalized_words(search_term)
    if not term_words:
        return False
    prompt_words = normalized_words(prompt)
    return all(any(word_matches(prompt_word, term_word) for prompt_word in prompt_words) for term_word in term_words)


def allowed_distance(search_term: str) -> int:
    """
    Return the number of typos to tolerate in a search term.

    Longer search terms tolerate more typos, and short ones none, because a short
    word is only a few edits away from many unrelated words. For example, ``API`` is
    within three edits of ``and``, ``the`` and ``any``.

    - Search terms of fewer than 5 characters: 0.
    - Search terms of 5 to 8 characters: 1.
    - Longer search terms: 2.

    Spaces are not counted.

    :param search_term: The search term.
    :type search_term: str

    :return: The maximum Levenshtein distance at which the search term still matches.
    :rtype: int
    """
    length = len(search_term.replace(" ", ""))
    if length < 5:
        return 0
    return 1 if length <= 8 else 2


def within_levenshtein_distance(prompt: str, search_term: str, threshold: Optional[int] = None) -> bool:
    """
    Check if the prompt contains the search term, allowing for typos.

    This function compares the search term, case-insensitively and without punctuation,
    with each run of consecutive words in the prompt that has as many words as the search
    term. It returns `True` if any run is within the search term's
    :func:`allowed_distance` of it, measured as Levenshtein distance. For example, the
    search term ``Lawrence McDaniel`` matches ``Lawrance McDaniel``, and ``Gobstopper``
    matches ``Gobbstopper``.

    :param prompt: The input string to search within.
    :type prompt: str
    :param search_term: The target string to compare against.
    :type search_term: str
    :param threshold: An optional maximum Levenshtein distance, which can only make
        the match stricter than :func:`allowed_distance`.
    :type threshold: Optional[int]

    :return: `True` if a run of words in the prompt is within the allowed distance of the search term,
        otherwise `False`. Search terms of fewer than 5 characters never match, because they tolerate no typos.
    :rtype: bool

    .. seealso::

        - :func:`allowed_distance`
        - :func:`simple_search`
        - :func:`does_refer_to`
        - `Levenshtein.distance <https://pypi.org/project/python-Levenshtein/>`_

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.nlp import within_levenshtein_distance

        prompt = "Who is Lawrance McDaniel?"
        print(within_levenshtein_distance(prompt, "Lawrence McDaniel"))  # True
        print(within_levenshtein_distance("any ideas?", "API"))          # False
    """
    term_words = normalized_words(search_term)
    if not term_words:
        return False
    term = " ".join(term_words)
    limit = allowed_distance(term)
    if threshold is not None:
        limit = min(limit, threshold)
    if limit <= 0:
        return False
    words = normalized_words(prompt)
    size = len(term_words)
    for i in range(len(words) - size + 1):
        if Levenshtein.distance(term, " ".join(words[i : i + size])) <= limit:
            return True
    return False


def does_refer_to(prompt: str, search_term: str, threshold: Optional[int] = None, fuzzy: Optional[bool] = None) -> bool:
    """
    Check if the prompt refers to the given string.

    This function determines whether a prompt refers to a search term by first cleaning
    the prompt with :func:`clean_prompt`, and then searching it with :func:`simple_search`.
    If typo tolerant matching is enabled, it then also tries
    :func:`within_levenshtein_distance`.

    :param prompt: The input string to analyze.
    :type prompt: str
    :param search_term: The target string to check for reference.
    :type search_term: str
    :param threshold: An optional maximum Levenshtein distance for typo tolerant matching.
        See :func:`within_levenshtein_distance`.
    :type threshold: Optional[int]
    :param fuzzy: Whether to tolerate typos. Defaults to the
        ``enable_plugin_fuzzy_matching`` waffle switch, which is on by default.
    :type fuzzy: Optional[bool]

    :return: `True` if the prompt refers to the search term, otherwise `False`.
    :rtype: bool

    .. important::

        Plugin selectors use this function to decide whether to select a plugin,
        which adds the plugin's system prompt and tools to the conversation. Typo
        tolerant matching selects plugins more often, and it is controlled by
        :attr:`SmarterWaffleSwitches.ENABLE_PLUGIN_FUZZY_MATCHING`.

    .. seealso::

        - :func:`clean_prompt`
        - :func:`simple_search`
        - :func:`within_levenshtein_distance`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.nlp import does_refer_to

        prompt = "WhoIsLawranceMcDaniel"
        print(does_refer_to(prompt, "Lawrence McDaniel", fuzzy=True))   # True
        print(does_refer_to(prompt, "Lawrence McDaniel", fuzzy=False))  # False
        print(does_refer_to(prompt, "John Doe", fuzzy=True))            # False
    """

    prompt = clean_prompt(prompt)

    if simple_search(prompt=prompt, search_term=search_term):
        return True

    if fuzzy is None:
        fuzzy = switch_is_active(SmarterWaffleSwitches.ENABLE_PLUGIN_FUZZY_MATCHING)
    if fuzzy and within_levenshtein_distance(prompt=prompt, search_term=search_term, threshold=threshold):
        return True

    # bust. we didn't find the target string in the prompt
    return False
