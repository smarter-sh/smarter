# pylint: disable=duplicate-code
# pylint: disable=E1101
"""Utility functions for the OpenAI Lambda functions"""
import datetime
import json  # library for interacting with JSON data https://www.json.org/json-en.html
import logging

from pydantic import SecretStr


logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.strftime("%Y-%m-%d")
        if isinstance(o, SecretStr):
            return "*** REDACTED ***"

        return super().default(o)


def recursive_sort_dict(d):
    """Recursively sort a dictionary by key."""
    return {k: recursive_sort_dict(v) if isinstance(v, dict) else v for k, v in sorted(d.items())}
