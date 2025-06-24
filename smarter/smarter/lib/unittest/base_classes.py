"""
Project level base classes for unit tests.
"""

import csv
import json
import logging
import unittest
from typing import Union

import yaml

from smarter.common.utils import hash_factory


logger = logging.getLogger(__name__)


class SmarterTestBase(unittest.TestCase):
    """Base class for all unit tests."""

    name: str

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test class."""
        super().setUpClass()
        cls.hash_suffix = SmarterTestBase.generate_hash_suffix()
        cls.name = "test" + cls.hash_suffix
        cls.uid = SmarterTestBase.generate_uid()

        logger.info("Setting up test class with hash suffix: %s", cls.hash_suffix)
        logger.info("Setting up test class with name: %s", cls.name)
        logger.info("Setting up test class with uid: %s", cls.uid)

    @classmethod
    def tearDownClass(cls) -> None:
        """Tear down the test class."""
        super().tearDownClass()

    @classmethod
    def generate_uid(cls) -> str:
        """Generate a unique identifier for the test."""
        return hash_factory(length=64)

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
    def generate_hash_suffix(length: int = 16) -> str:
        """Generate a unique hash suffix for test data."""
        return hash_factory(length=length)
