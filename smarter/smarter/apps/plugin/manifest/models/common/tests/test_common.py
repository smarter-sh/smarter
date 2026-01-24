"""Unit tests for common plugin manifest models."""

import logging

from pydantic_core import ValidationError as PydanticValidationError

from smarter.apps.plugin.manifest.models.common import (
    Parameter,
    ParameterType,
    RequestHeader,
    TestValue,
    UrlParam,
)
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.unittest.base_classes import SmarterTestBase

logger = logging.getLogger(__name__)
HERE = __name__


class TestUrlParam(SmarterTestBase):
    """Unit tests for UrlParam model."""

    def test_initialization(self):
        param = UrlParam(key="exampleKey", value="exampleValue")
        self.assertEqual(param.key, "exampleKey")
        self.assertEqual(param.value, "exampleValue")

    def test_invalid_key(self):
        with self.assertRaises(SmarterValueError):
            UrlParam(key="bad key!", value="value")

    def test_invalid_value(self):
        with self.assertRaises(SmarterValueError):
            UrlParam(key="validKey", value="bad value!")


class TestRequestHeader(SmarterTestBase):
    """Unit tests for RequestHeader model."""

    def test_initialization(self):
        header = RequestHeader(name="X-Test-Header", value="headerValue")
        self.assertEqual(header.name, "X-Test-Header")
        self.assertEqual(header.value, "headerValue")

    def test_invalid_name(self):
        with self.assertRaises(SmarterValueError):
            RequestHeader(name="X Test Header", value="value")

    def test_invalid_value(self):
        with self.assertRaises(SmarterValueError):
            RequestHeader(name="X-Test-Header", value="bad\nvalue")


class TestTestValue(SmarterTestBase):
    """Unit tests for TestValue model."""

    def test_initialization(self):
        test_value = TestValue(name="username", value="admin")
        self.assertEqual(test_value.name, "username")
        self.assertEqual(test_value.value, "admin")

    def test_value_type_conversion(self):
        test_value = TestValue(name="limit", value=1)
        self.assertEqual(test_value.value, "1")

    def test_none_value(self):
        test_value = TestValue(name="optional", value=None)
        self.assertIsNone(test_value.value)


class TestParameter(SmarterTestBase):
    """Unit tests for Parameter model."""

    def test_initialization(self):
        param = Parameter(name="max_cost", type=ParameterType.STRING, description="desc", required=True, default="100")
        self.assertEqual(param.name, "max_cost")
        self.assertEqual(param.type, ParameterType.STRING)
        self.assertEqual(param.description, "desc")
        self.assertTrue(param.required)
        self.assertEqual(param.default, "100")

    def test_enum_and_default_valid(self):
        param = Parameter(name="unit", type=ParameterType.STRING, enum=["Celsius", "Fahrenheit"], default="Celsius")
        self.assertEqual(param.default, "Celsius")

    def test_enum_and_default_invalid(self):
        with self.assertRaises(SmarterValueError):
            Parameter(name="unit", type=ParameterType.STRING, enum=["Celsius", "Fahrenheit"], default="Kelvin")
