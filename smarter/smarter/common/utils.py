# pylint: disable=duplicate-code
# pylint: disable=E1101
"""Utility functions for the OpenAI Lambda functions"""
import hashlib
import json  # library for interacting with JSON data https://www.json.org/json-en.html
import logging
import urllib.parse
from datetime import datetime

from pydantic import SecretStr


logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""

    def default(self, o):
        if isinstance(o, datetime):
            return o.strftime("%Y-%m-%d")
        if isinstance(o, SecretStr):
            return "*** REDACTED ***"

        return super().default(o)


def recursive_sort_dict(d):
    """Recursively sort a dictionary by key."""
    return {k: recursive_sort_dict(v) if isinstance(v, dict) else v for k, v in sorted(d.items())}


def dict_is_contained_in(dict1, dict2):
    for key, value in dict1.items():
        if key not in dict2:
            print(f"the key {key} is not present in the model dict: ")
            return False
        if isinstance(value, dict):
            if not dict_is_contained_in(value, dict2[key]):
                print("dict not in the model dict: ", value)
                return False
        else:
            if dict2[key] != value:
                print(f"value {value} is not present in the model dict: ")
                return False
    return True


def generate_key(unique_string: str) -> str:
    """
    Generate a session key based on a unique string and the current datetime.
    """
    key_string = unique_string + str(datetime.now())
    session_key = hashlib.sha256(key_string.encode()).hexdigest()
    logger.info("Generated new session key: %s", session_key)
    return session_key


def clean_url(url: str) -> str:
    """
    Clean the url of any query strings and trailing '/config/' strings.
    """
    parsed_url = urllib.parse.urlparse(url)
    retval = parsed_url._replace(query="").geturl()
    return retval
