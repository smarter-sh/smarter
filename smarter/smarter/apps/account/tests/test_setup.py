# pylint: disable=wrong-import-position
# pylint: disable=duplicate-code
"""Test Search Lambda plugin_data."""

import os

# python stuff
from smarter.lib import json


HERE = os.path.abspath(os.path.dirname(__file__))


def get_test_file(filename: str):
    """Load a mock lambda_index event."""
    path = os.path.join(HERE, "mock_data", filename)
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def get_test_file_path(filename: str):
    """Load a mock lambda_index event."""
    path = os.path.join(HERE, "mock_data", filename)
    return path
