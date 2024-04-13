# pylint: disable=wrong-import-position
# pylint: disable=duplicate-code
"""Test Search Lambda plugin_data."""

# python stuff
import json
import os
import sys
from pathlib import Path

import yaml


HERE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = str(Path(HERE).parent.parent.parent.parent)


sys.path.append(PROJECT_ROOT)  # noqa: E402


def noop():
    """Test to ensure that test suite setup works and is importable."""


def get_test_file(filename: str):
    """Load a mock lambda_index event."""
    path = os.path.join(HERE, "mock_data", filename)
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def get_test_file_yaml(filename: str):
    """Load a mock yaml file"""
    path = os.path.join(HERE, "mock_data", filename)
    with open(path, encoding="utf-8") as file:
        return yaml.safe_load(file)


def get_test_file_path(filename: str):
    """Load a mock lambda_index event."""
    path = os.path.join(HERE, "mock_data", filename)
    return path
