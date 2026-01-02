"""
Project level base classes for unit tests.
"""

import csv
import logging
import unittest
from typing import Union

import yaml
from django.http import HttpRequest
from django.test import RequestFactory

from smarter.common.classes import SmarterHelperMixin
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.utils import camel_to_snake, hash_factory
from smarter.lib import json


logger = logging.getLogger(__name__)
HERE = __name__


class SmarterTestBase(unittest.TestCase, SmarterHelperMixin):
    """Base class for all unit tests."""

    name: str
    smarter_test_base_logger_prefix = formatted_text(f"{HERE}.SmarterTestBase()")

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test class."""
        super().setUpClass()
        logger.info("%s.setUpClass()", cls.smarter_test_base_logger_prefix)
        cls.hash_suffix = SmarterTestBase.generate_hash_suffix()
        cls.name = camel_to_snake("smarterTestBase_" + cls.hash_suffix)
        cls.uid = SmarterTestBase.generate_uid()

        logger.info(
            "%s.setUpClass() Setting up test class with hash suffix: %s",
            cls.smarter_test_base_logger_prefix,
            cls.hash_suffix,
        )
        logger.info(
            "%s.setUpClass() Setting up test class with name: %s", cls.smarter_test_base_logger_prefix, cls.name
        )
        logger.info("%s.setUpClass() Setting up test class with uid: %s", cls.smarter_test_base_logger_prefix, cls.uid)

    @classmethod
    def tearDownClass(cls) -> None:
        """Tear down the test class."""
        logger.info("%s.tearDownClass()", cls.smarter_test_base_logger_prefix)
        super().tearDownClass()

    @classmethod
    def generate_uid(cls) -> str:
        """Generate a unique identifier for the test."""
        return hash_factory(length=64)

    @classmethod
    def get_readonly_yaml_file(cls, file_path) -> dict:
        """Read a YAML file in read-only mode."""
        with open(file_path, encoding="utf-8") as file:
            return yaml.safe_load(file)

    @classmethod
    def get_readonly_csv_file(cls, file_path) -> Union[dict, list[dict]]:
        """Read a CSV file in read-only mode."""
        with open(file_path, encoding="utf-8") as file:
            reader = csv.DictReader(file)
            return list(reader)

    @classmethod
    def get_readonly_json_file(cls, file_path) -> Union[dict, list]:
        """Read a JSON file in read-only mode."""
        with open(file_path, encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def generate_hash_suffix(length: int = 16) -> str:
        """Generate a unique hash suffix for test data."""
        return hash_factory(length=length)

    def create_generic_request(self, url="http://example.com") -> HttpRequest:
        """Create a generic HTTP request for testing purposes."""
        factory = RequestFactory()
        json_data = {
            "session_key": "6f3bdd1981e0cac2de5fdc7afc2fb4e565826473a124153220e9f6bf49bca67b",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "assistant",
                    "content": "Welcome to Smarter!. Following are some example prompts: blah blah blah",
                },
                {"role": "smarter", "content": 'Tool call: function_calling_plugin_0002({"inquiry_type":"about"})'},
                {"role": "user", "content": "Hello, World!"},
            ],
        }
        json_data = json.dumps(json_data).encode("utf-8")

        headers = {}
        data = {}

        request: HttpRequest = factory.post(path=url, data=data, content_type="application/json", headers=headers)
        return request
