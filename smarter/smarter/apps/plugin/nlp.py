"""Natural language processing functions for OpenAI API-compatible providers."""

import re
import string
from functools import lru_cache
from typing import Any, Optional

import Levenshtein

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

from .signals import search_term_matched

logger = logging.getLogger(__name__)

PLURAL_SUFFIXES = ("s", "es")
"""Suffixes with which a prompt's word still matches a search term's word, e.g. Gobstoppers and Gobstopper."""

THESAURUS_MAX_SENSES = 2
"""
The number of a word's most common senses from which its synonyms come.

A word has many senses in WordNet, ordered from the most to the least common. For example,
the fifth noun sense of ``car`` is an elevator car. Synonyms of rare senses would select
plugins for prompts that have nothing to do with them. For the same reason, a word that is a
noun only has the synonyms of its noun senses: the verb ``image`` means ``see``, so that
``let me see the code`` would otherwise refer to ``image``.
"""

THESAURUS_MIN_WORD_LENGTH = 3
"""
Search term words shorter than this are matched exactly, never by synonym.

Short words are mostly pronouns and abbreviations, whose WordNet senses are rarely the
intended ones. For example, ``me`` is the abbreviation of Maine.
"""

WORDNET_DOWNLOAD_HELP = "Install it with: python -m nltk.downloader wordnet. The Docker image installs it into /home/smarter_user/nltk_data."


class MatchMethod:
    """How :func:`does_refer_to` matched a search term.

    Sent as the ``method`` of :data:`search_term_matched`.
    """

    EXACT = "exact"
    """Every word of the search term is in the prompt.

    See :func:`simple_search`.
    """
    FUZZY = "fuzzy"
    """The search term is in the prompt, with a typo or two.

    See :func:`within_levenshtein_distance`.
    """
    THESAURUS = "thesaurus"
    """The search term, or a synonym of each of its words, is in the prompt.

    See :func:`thesaurus_match`.
    """


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


@lru_cache(maxsize=1)
def wordnet() -> Optional[Any]:
    """
    Return the WordNet corpus reader, loading the corpus on first use.

    `WordNet <https://wordnet.princeton.edu/>`__ is the thesaurus of :func:`thesaurus_match`.
    It is read with `NLTK <https://www.nltk.org/>`__, whose corpus data must be installed
    separately. If it is not installed, a warning is logged once, and thesaurus matching is
    disabled.

    :return: The ``nltk.corpus.wordnet`` reader, or None if the corpus is not installed.
    """
    # pylint: disable=import-outside-toplevel
    from nltk.corpus import wordnet as wn

    try:
        wn.ensure_loaded()
    except LookupError:
        logger.warning(
            "The NLTK WordNet corpus is not installed, so thesaurus matching is disabled. %s", WORDNET_DOWNLOAD_HELP
        )
        return None
    return wn


@lru_cache(maxsize=4096)
def synonyms(phrase: str, nouns_only: bool = False) -> frozenset[str]:
    """
    Return the synonyms of a word or phrase, from the most common senses of WordNet.

    Synonyms come from the first :data:`THESAURUS_MAX_SENSES` noun senses of the phrase, or,
    if it is not a noun, from the first senses of each of its other parts of speech. They are
    lower case, and multi-word synonyms have spaces, e.g. ``motor vehicle``. The
    phrase itself is not included.

    :param phrase: A lower case word, e.g. ``car``, or phrase, e.g. ``black and white``.
    :type phrase: str
    :param nouns_only: Whether a phrase that is not a noun has no synonyms, rather than those of its other parts of speech.
    :type nouns_only: bool

    :return: The synonyms, which are empty if WordNet is not installed, or does not know the phrase.
    :rtype: frozenset[str]

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.nlp import synonyms

        print(sorted(synonyms("car")))
        # Output: ['auto', 'automobile', 'machine', 'motorcar', 'railcar', 'railroad car', 'railway car']
        print(sorted(synonyms("image")))
        # Output: ['mental image', 'persona']
    """
    wn = wordnet()
    if wn is None or not phrase:
        return frozenset()
    key = phrase.replace(" ", "_")
    synsets = wn.synsets(key, pos=wn.NOUN)[:THESAURUS_MAX_SENSES]
    if not synsets and not nouns_only:
        for pos in (wn.VERB, wn.ADJ, wn.ADV):
            synsets += wn.synsets(key, pos=pos)[:THESAURUS_MAX_SENSES]
    retval: set[str] = set()
    for synset in synsets:
        retval.update(lemma.name().replace("_", " ").lower() for lemma in synset.lemmas())
    retval.discard(phrase)
    return frozenset(retval)


def contains_phrase(prompt_words: list[str], phrase: str) -> bool:
    """
    Check if a list of words contains a phrase, as consecutive words.

    Each word matches with :func:`word_matches`, so plurals match, e.g. ``motor vehicles``
    contains the phrase ``motor vehicle``.

    :param prompt_words: The prompt's words, as returned by :func:`normalized_words`.
    :type prompt_words: list[str]
    :param phrase: A lower case word or phrase.
    :type phrase: str

    :return: `True` if the words contain the phrase, otherwise `False`.
    :rtype: bool
    """
    phrase_words = normalized_words(phrase)
    if not phrase_words:
        return False
    size = len(phrase_words)
    return any(
        all(word_matches(prompt_words[i + j], phrase_words[j]) for j in range(size))
        for i in range(len(prompt_words) - size + 1)
    )


def thesaurus_match(prompt: str, search_term: str) -> Optional[str]:
    """
    Check if the prompt contains the search term, or synonyms of it, from the WordNet thesaurus.

    The prompt matches if it contains a synonym of the whole search term, e.g. ``monochrome``
    for ``black and white``, or if, for each word of the search term, it contains the word, one
    of its :func:`synonyms`, e.g. ``automobile`` for ``car``, or a noun of which it is a
    synonym. WordNet's synonyms are not symmetric: ``image`` is a synonym of ``picture``, but
    ``picture`` is not a synonym of the noun ``image``. Only nouns count in this direction,
    since ``weather`` is a synonym of the verb ``endure``. Words shorter than
    :data:`THESAURUS_MIN_WORD_LENGTH` must match exactly. Synonyms come only from each word's
    most common senses, to keep plugin selection precise.

    :param prompt: The input string to search within.
    :type prompt: str
    :param search_term: The target string or phrase to look for.
    :type search_term: str

    :return: The words of the prompt that matched, e.g. ``automobile``, or None if the prompt
        does not match, or WordNet is not installed.
    :rtype: Optional[str]

    .. seealso::

        - :func:`synonyms`
        - :func:`does_refer_to`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.nlp import thesaurus_match

        print(thesaurus_match("I want to buy an automobile", "car"))  # 'automobile'
        print(thesaurus_match("show me a picture of a cat", "image"))  # 'picture'
        print(thesaurus_match("what is the weather", "car"))           # None
    """
    term_words = normalized_words(search_term)
    prompt_words = normalized_words(prompt)
    if not term_words or not prompt_words or wordnet() is None:
        return None
    if len(term_words) > 1:
        for synonym in sorted(synonyms(" ".join(term_words))):
            if contains_phrase(prompt_words, synonym):
                return synonym
    matched: list[str] = []
    for term_word in term_words:
        if any(word_matches(prompt_word, term_word) for prompt_word in prompt_words):
            matched.append(term_word)
            continue
        if len(term_word) < THESAURUS_MIN_WORD_LENGTH:
            return None
        synonym = next(
            (synonym for synonym in sorted(synonyms(term_word)) if contains_phrase(prompt_words, synonym)), None
        )
        if synonym is None:
            synonym = next(
                (
                    prompt_word
                    for prompt_word in prompt_words
                    if len(prompt_word) >= THESAURUS_MIN_WORD_LENGTH
                    and any(word_matches(term_word, word) for word in synonyms(prompt_word, nouns_only=True))
                ),
                None,
            )
        if synonym is None:
            return None
        matched.append(synonym)
    return " ".join(matched)


def does_refer_to(
    prompt: str,
    search_term: str,
    threshold: Optional[int] = None,
    fuzzy: Optional[bool] = None,
    use_thesaurus: Optional[bool] = None,
) -> bool:
    """
    Check if the prompt refers to the given string.

    This function determines whether a prompt refers to a search term by first cleaning
    the prompt with :func:`clean_prompt`, and then searching it with :func:`simple_search`.
    If typo tolerant matching is enabled, it then also tries
    :func:`within_levenshtein_distance` and, if thesaurus matching is enabled,
    :func:`thesaurus_match`. When the prompt refers to the search term, the
    :data:`~smarter.apps.plugin.signals.search_term_matched` signal is sent, with the
    :class:`MatchMethod` that matched.

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
    :param use_thesaurus: Whether to match synonyms, from the WordNet thesaurus. Defaults to
        the ``enable_plugin_thesaurus_matching`` waffle switch, which is on by default.
    :type use_thesaurus: Optional[bool]

    :return: `True` if the prompt refers to the search term, otherwise `False`.
    :rtype: bool

    .. important::

        Plugin selectors use this function to decide whether to select a plugin,
        which adds the plugin's system prompt and tools to the conversation. Typo
        tolerant matching selects plugins more often, and it is controlled by
        :attr:`SmarterWaffleSwitches.ENABLE_PLUGIN_FUZZY_MATCHING`. Thesaurus matching
        selects plugins more often still, and it is controlled by
        :attr:`SmarterWaffleSwitches.ENABLE_PLUGIN_THESAURUS_MATCHING`.

    .. seealso::

        - :func:`clean_prompt`
        - :func:`simple_search`
        - :func:`within_levenshtein_distance`
        - :func:`thesaurus_match`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.nlp import does_refer_to

        prompt = "WhoIsLawranceMcDaniel"
        print(does_refer_to(prompt, "Lawrence McDaniel", fuzzy=True))   # True
        print(does_refer_to(prompt, "Lawrence McDaniel", fuzzy=False))  # False
        print(does_refer_to(prompt, "John Doe", fuzzy=True))            # False
        print(does_refer_to("buy an automobile", "car", use_thesaurus=True))  # True
    """

    original_prompt = prompt
    prompt = clean_prompt(prompt)

    def matched(method: str, matched_text: Optional[str] = None) -> bool:
        search_term_matched.send(
            sender=does_refer_to,
            prompt=original_prompt,
            search_term=search_term,
            method=method,
            matched_text=matched_text,
        )
        return True

    if simple_search(prompt=prompt, search_term=search_term):
        return matched(MatchMethod.EXACT)

    if fuzzy is None:
        fuzzy = switch_is_active(SmarterWaffleSwitches.ENABLE_PLUGIN_FUZZY_MATCHING)
    if fuzzy and within_levenshtein_distance(prompt=prompt, search_term=search_term, threshold=threshold):
        return matched(MatchMethod.FUZZY)

    if use_thesaurus is None:
        use_thesaurus = switch_is_active(SmarterWaffleSwitches.ENABLE_PLUGIN_THESAURUS_MATCHING)
    if use_thesaurus:
        synonym = thesaurus_match(prompt=prompt, search_term=search_term)
        if synonym is not None:
            return matched(MatchMethod.THESAURUS, synonym)

    # bust. we didn't find the target string in the prompt
    return False
