"""Natural language processing functions for the OpenAI API."""

import re
import string

import Levenshtein


def clean_prompt(prompt: str) -> str:
    """
    Clean up the prompt by adding spaces before capital letters.
    Example: converts "WhoIsLawrenceMcDaniel" to "Who Is Lawrence McDaniel"
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
    """Split a string on spaces and return a list of lowercase words."""
    return [word.lower() for word in string_of_words.split()]


def simple_search(prompt: str, search_term: str) -> bool:
    """Check if the prompt contains the target string."""

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
    """Check if the prompt is within the given Levenshtein distance of the target string."""
    words = lower_case_splitter(prompt)
    names = [word for word in words if word.istitle()]
    for name in names:
        distance = Levenshtein.distance(search_term, name)
        if distance <= threshold:
            return True
    return False


def does_refer_to(prompt: str, search_term: str, threshold=3) -> bool:
    """Check if the prompt refers to the given string."""

    prompt = clean_prompt(prompt)

    if simple_search(prompt=prompt, search_term=search_term):
        return True

    if within_levenshtein_distance(prompt=prompt, search_term=search_term, threshold=threshold):
        return True

    # bust. we didn't find the target string in the prompt
    return False
