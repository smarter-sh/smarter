"""Natural language processing functions for OpenAI API-compatible providers."""

import re
import string

import Levenshtein


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
        - :func:`simple_search`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.nlp import lower_case_splitter

        s = "The Quick Brown Fox"
        print(lower_case_splitter(s))
        # Output: ['the', 'quick', 'brown', 'fox']

    """
    return [word.lower() for word in string_of_words.split()]


def simple_search(prompt: str, search_term: str) -> bool:
    """
    Check if the prompt contains the target string.

    This function performs a case-insensitive search for the `search_term` within the `prompt`.
    It also checks if all tokens in the search term appear in the prompt, regardless of order.

    :param prompt: The input string to search within.
    :type prompt: str
    :param search_term: The target string or phrase to look for.
    :type search_term: str

    :return: `True` if the search term is found in the prompt, otherwise `False`.
    :rtype: bool

    .. tip::

        Use this function for simple keyword or phrase matching in user prompts or text analysis.

    .. caution::

        This function does not perform fuzzy matching or handle typos. For more advanced matching,
        consider using :func:`within_levenshtein_distance`.

    .. seealso::

        - :func:`lower_case_splitter`
        - :func:`within_levenshtein_distance`
        - :func:`does_refer_to`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.nlp import simple_search

        prompt = "Find all weather plugins for New York"
        print(simple_search(prompt, "weather plugins"))  # True
        print(simple_search(prompt, "Weather"))          # True
        print(simple_search(prompt, "California"))       # False

    """

    # simplest possible case: the search term is in the prompt
    if search_term.lower() in prompt.lower():
        return True

    prompt_words = lower_case_splitter(prompt)
    token_count = len(search_term.split())
    found_count = 0
    for token in lower_case_splitter(search_term):
        if token in prompt_words:
            found_count += 1
        if found_count >= token_count:
            return True
    return False


def within_levenshtein_distance(prompt: str, search_term: str, threshold: int = 3) -> bool:
    """
    Check if the prompt is within the given Levenshtein distance of the target string.

    This function compares each title-cased word in the prompt to the `search_term` using the
    Levenshtein distance metric. If any word is within the specified `threshold`, the function
    returns `True`. Useful for fuzzy matching and typo-tolerant search.

    :param prompt: The input string to search within.
    :type prompt: str
    :param search_term: The target string to compare against.
    :type search_term: str
    :param threshold: The maximum allowed Levenshtein distance for a match (default: 3).
    :type threshold: int

    :return: `True` if a word in the prompt is within the threshold distance of the search term, otherwise `False`.
    :rtype: bool

    .. tip::

        Adjust the `threshold` parameter to control the strictness of fuzzy matching.

    .. caution::

        Only title-cased words in the prompt are considered for comparison.

    .. seealso::

        - :func:`simple_search`
        - :func:`does_refer_to`
        - `Levenshtein.distance <https://pypi.org/project/python-Levenshtein/>`_

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.nlp import within_levenshtein_distance

        prompt = "Find all plugins for Lawrance McDaniel"
        print(within_levenshtein_distance(prompt, "Lawrence", threshold=2))  # True

    """
    words = lower_case_splitter(prompt)
    names = [word for word in words if word.istitle()]
    for name in names:
        distance = Levenshtein.distance(search_term, name)
        if distance <= threshold:
            return True
    return False


def does_refer_to(prompt: str, search_term: str, threshold=3) -> bool:
    """
    Check if the prompt refers to the given string.

    This function determines whether a prompt refers to a target string by first cleaning the prompt,
    then performing both direct and fuzzy matching. It uses :func:`simple_search` for exact or token-based
    matches, and :func:`within_levenshtein_distance` for typo-tolerant fuzzy matches.

    :param prompt: The input string to analyze.
    :type prompt: str
    :param search_term: The target string to check for reference.
    :type search_term: str
    :param threshold: The maximum Levenshtein distance for fuzzy matching (default: 3).
    :type threshold: int

    :return: `True` if the prompt refers to the search term, otherwise `False`.
    :rtype: bool

    .. important::

        This function combines both exact and fuzzy matching for robust reference detection.

    .. tip::

        Adjust the `threshold` parameter for stricter or looser fuzzy matching.

    .. seealso::

        - :func:`clean_prompt`
        - :func:`simple_search`
        - :func:`within_levenshtein_distance`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.nlp import does_refer_to

        prompt = "WhoIsLawranceMcDaniel"
        print(does_refer_to(prompt, "Lawrence McDaniel"))  # True
        print(does_refer_to(prompt, "John Doe"))           # False

    """

    prompt = clean_prompt(prompt)

    if simple_search(prompt=prompt, search_term=search_term):
        return True

    if within_levenshtein_distance(prompt=prompt, search_term=search_term, threshold=threshold):
        return True

    # bust. we didn't find the target string in the prompt
    return False
