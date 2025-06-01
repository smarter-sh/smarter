# pylint: disable=wrong-import-position
"""Test Search Lambda function."""

# python stuff
import json
import os
import sys


HERE = os.path.abspath(os.path.dirname(__file__))
PYTHON_ROOT = os.path.dirname(HERE)
sys.path.append(PYTHON_ROOT)  # noqa: E402


def get_test_file(filename: str):
    """Load a mock lambda_index event."""
    path = os.path.join(HERE, "mock_data", filename)
    with open(path, encoding="utf-8") as file:
        return json.load(file)
