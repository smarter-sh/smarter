"""Project level base classes for unit tests."""

import csv
import unittest
from typing import Union

import yaml
from django.core.cache import cache
from django.http import HttpRequest
from django.test import RequestFactory

from smarter.common.mixins import SmarterHelperMixin
from smarter.common.utils import hash_factory, to_snake_case
from smarter.lib import json, logging
from smarter.lib.django.waffle.is_active import clear_switch_cache
from smarter.lib.typing import SmarterDictType

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)

SERVER_RENDERED_PAGE = "/dashboard/passthrough/"
"""
A console page that Django still renders, for tests of its frame.

The frame is ``templates/dashboard/base.html``'s: the sidebar, the user menu, the welcome dialog, the onboarding
hints and the tips: the Prompt Passthrough's, which is on by default. The dashboard, the resource lists and the
Extensions console moved into the single-page console, which serves their paths with its ``index.html`` (ADR-035).
"""


class SmarterTestBase(unittest.TestCase, SmarterHelperMixin):
    """
    Base class for all unit tests.

    It gives each test class a unique ``hash_suffix``, ``name`` and ``uid``, from which tests
    name the resources they create, so that test classes don't collide. It clears the Django
    cache and the waffle switch cache before each test class, logs a banner at the start and
    end of each test, and reads test data files.

    It has no transaction rollback: a test deletes everything that it creates.
    """

    name: str
    #: The log prefix of this class's messages. A subclass can override it.
    smarter_test_base_logger_prefix = f"{logger_prefix}.SmarterTestBase()"
    #: The width of the banners that are logged at the start and end of each test.
    line_width = 150

    @classmethod
    def _banner(cls, title: str, fill: str) -> str:
        """
        Return ``title`` centered in a line of ``fill`` characters, ``line_width`` wide.

        :param title: The title.
        :param fill: The character on each side of the title.
        :returns: The banner.
        """
        fill_width = (cls.line_width - len(title)) // 2
        fill_characters = fill * fill_width
        banner = fill_characters + title + fill_characters
        return banner

    @classmethod
    def setUpClass(cls) -> None:
        """
        Set up the test class: give it a unique ``hash_suffix``, ``name`` and ``uid``, and clear the caches.

        The Django cache and the waffle switch cache are cleared, so that a test class doesn't see
        values that an earlier one cached.
        """
        super().setUpClass()
        title = f" {SmarterTestBase.smarter_test_base_logger_prefix}.setUpClass() "
        msg = cls._banner(title, "*")
        logger.debug(msg)
        cls.hash_suffix = SmarterTestBase.generate_hash_suffix()
        cls.name = str(to_snake_case("smarterTestBase_" + cls.hash_suffix))
        cls.uid = SmarterTestBase.generate_uid()
        cache.clear()
        clear_switch_cache()

        logger.debug(
            "%s.setUpClass() Setting up test class with hash suffix: %s",
            cls.smarter_test_base_logger_prefix,
            cls.hash_suffix,
        )
        logger.debug(
            "%s.setUpClass() Setting up test class with name: %s", cls.smarter_test_base_logger_prefix, cls.name
        )
        logger.debug("%s.setUpClass() Setting up test class with uid: %s", cls.smarter_test_base_logger_prefix, cls.uid)
        logger.debug(
            "%s.setUpClass() %s",
            cls.smarter_test_base_logger_prefix,
            logging.SmarterFormattedText.text("Django cache has been cleared", logging.SmarterFormattedText.DARK_RED),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        """Tear down the test class."""
        super().tearDownClass()

    def setUp(self) -> None:
        """Set up the test: log a banner with the test method's name."""
        super().setUp()
        title = f" {SmarterTestBase.smarter_test_base_logger_prefix}.{self._testMethodName}() "
        msg = self._banner(title, "-")
        logger.debug(msg)

    def tearDown(self) -> None:
        """Tear down the test: log a banner with the test method's name."""
        title = f" {SmarterTestBase.smarter_test_base_logger_prefix}.tearDown() {self._testMethodName} "
        msg = self._banner(title, "-")
        logger.debug(msg)
        super().tearDown()

    @classmethod
    def generate_uid(cls) -> str:
        """
        Generate a unique identifier for the test.

        :returns: A random 64 character hash.
        """
        return hash_factory(length=64)

    @classmethod
    def get_readonly_yaml_file(cls, file_path: str) -> Union[SmarterDictType, list, None]:
        """
        Read a YAML file in read-only mode.

        :param file_path: The path of the file.
        :returns: What the file holds, usually a dict, e.g. a manifest; a list; or None if the file
            is empty.
        """
        with open(file_path, encoding="utf-8") as file:
            data = yaml.safe_load(file)
            return data

    @classmethod
    def get_readonly_csv_file(cls, file_path: str) -> list[dict[str, str]]:
        """
        Read a CSV file in read-only mode.

        :param file_path: The path of the file. Its first row holds the column names.
        :returns: One dict per row, from column name to value.
        """
        with open(file_path, encoding="utf-8") as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            return rows

    @classmethod
    def get_readonly_json_file(cls, file_path: str) -> Union[SmarterDictType, list[SmarterDictType]]:
        """
        Read a JSON file in read-only mode.

        :param file_path: The path of the file.
        :returns: What the file holds: an object, or a list of objects.
        """
        with open(file_path, encoding="utf-8") as file:
            data = json.load(file)
            return data

    @staticmethod
    def generate_hash_suffix(length: int = 16) -> str:
        """
        Generate a unique hash suffix for test data.

        :param length: The suffix's length.
        :returns: A random hash.
        """
        return hash_factory(length=length)

    def create_generic_request(self, url: str = "http://example.com") -> HttpRequest:
        """
        Create a generic POST request for testing purposes.

        The request's body is an empty JSON object. The sample chat body that this method builds
        is not sent.

        :param url: The request's path.
        :returns: The request, from Django's :class:`~django.test.RequestFactory`.
        """
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
