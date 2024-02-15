# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
# pylint: disable=R0801
"""Test lambda_openai_v2 function."""

# python stuff
import json
import os
import sys
import unittest
from pathlib import Path


HERE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = str(Path(HERE).parent.parent)
PYTHON_ROOT = str(Path(PROJECT_ROOT).parent)
if PYTHON_ROOT not in sys.path:
    sys.path.append(PYTHON_ROOT)  # noqa: E402


from smarter.apps.api.openai_function_calling.function_weather import (
    get_current_weather,
    weather_tool_factory,
)


class TestLambdaOpenaiFunctionWeather(unittest.TestCase):
    """Test OpenAI Function Calling hook for refers_to."""

    def setUp(self):
        """Set up test fixtures."""

    # pylint: disable=broad-exception-caught
    def test_get_current_weather(self):
        """Test default return value of get_current_weather()"""
        retval = get_current_weather("London, UK")
        self.assertIsInstance(retval, str)
        try:
            json.loads(retval)
        except Exception:
            self.fail("get_current_weather() returned invalid JSON")

    def test_weather_tool_factory(self):
        """Test integrity weather_tool_factory()"""
        wtf = weather_tool_factory()
        self.assertIsInstance(wtf, dict)

        self.assertIsInstance(wtf, dict)
        self.assertTrue("type" in wtf)
        self.assertTrue("function" in wtf)
