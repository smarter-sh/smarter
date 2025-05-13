"""
Project level base classes for unit tests.
"""

import csv
import hashlib
import json
import logging
import random
import unittest
from typing import Union

import yaml


logger = logging.getLogger(__name__)


class SmarterTestBase(unittest.TestCase):
    """Base class for all unit tests."""

    name: str = None

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test class."""
        super().setUpClass()
        cls.hash_suffix = SmarterTestBase.generate_hash_suffix()
        cls.name = "test_" + cls.hash_suffix
        logger.info("Setting up test class with hash suffix: %s", cls.hash_suffix)
        logger.info("Setting up test class with name: %s", cls.name)

    @classmethod
    def tearDownClass(cls) -> None:
        """Tear down the test class."""
        super().tearDownClass()
        cls.hash_suffix = None
        cls.name = None

    @classmethod
    def get_readonly_yaml_file(cls, file_path) -> dict:
        with open(file_path, encoding="utf-8") as file:
            return yaml.safe_load(file)

    @classmethod
    def get_readonly_csv_file(cls, file_path) -> Union[dict, list[dict]]:
        with open(file_path, encoding="utf-8") as file:
            reader = csv.DictReader(file)
            return list(reader)

    @classmethod
    def get_readonly_json_file(cls, file_path) -> Union[dict, list]:
        with open(file_path, encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def generate_hash_suffix() -> str:
        """Generate a unique hash suffix for test data."""
        return "_" + hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()[:16]
