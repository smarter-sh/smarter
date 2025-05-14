# pylint: disable=duplicate-code
# pylint: disable=E1101
"""Utility functions for the OpenAI Lambda functions"""
import csv
import json  # library for interacting with JSON data https://www.json.org/json-en.html
import logging
import re
from datetime import datetime

import yaml
from pydantic import SecretStr


logger = logging.getLogger(__name__)


def get_readonly_yaml_file(file_path) -> dict:
    with open(file_path, encoding="utf-8") as file:
        return yaml.safe_load(file)


def get_readonly_csv_file(file_path):
    with open(file_path, encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""

    def default(self, o):
        if isinstance(o, datetime):
            return o.strftime("%Y-%m-%d")
        if isinstance(o, SecretStr):
            return "*** REDACTED ***"

        return super().default(o)


def camel_to_snake(name):
    """
    Converts camelCase or poorly formatted names to snake_case.
    examples:
        camel_to_snake("camelCase") -> "camel_case"
        camel_to_snake("CamelCase") -> "camel_case"
        camel_to_snake("Camel Case") -> "camel_case"
        camel_to_snake("camel case") -> "camel_case"
        camel_to_snake("camelCaseWithSpaces") -> "camel_case_with_spaces"
        camel_to_snake("CamelCaseWithSpaces") -> "camel_case_with_spaces"
        camel_to_snake("Camel Case With Spaces") -> "camel_case_with_spaces"
        camel_to_snake("MYEverlastingSUPERDUPERGobstopper") -> "my_everlasting_superduper_gobstopper"
    Args:
        name (str): The name to convert.
    Returns:
        str: The converted name in snake_case.
    """
    name = str(name or "")
    name = name.replace(" ", "_").replace("-", "_")

    # Split lowercase-uppercase boundary
    name = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)

    # Handle consecutive uppercase letters followed by lowercase letters
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)

    # Reduce multiple underscores to a single underscore
    name = re.sub(r"_+", "_", name)

    # Remove non-alphanumeric characters except underscores
    name = re.sub(r"[^\w]", "", name)

    return name.lower()


def camel_to_snake_dict(dictionary: dict) -> dict:
    """Converts camelCase dict keys to snake_case."""

    def convert(name: str):
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    retval = {}
    for key, value in dictionary.items():
        if isinstance(value, dict):
            value = camel_to_snake_dict(value)
        new_key = convert(key)
        retval[new_key] = value
    return retval


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
