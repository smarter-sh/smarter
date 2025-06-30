"""
Test mixins for the plugin module.
"""

import json
import logging

from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.unittest.base_classes import SmarterTestBase

from ..function_weather import get_current_weather, weather_tool_factory


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING) and level <= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class GetCurrentWeather(SmarterTestBase):
    """
    Test get_current_weather() functions.
    """

    def test_get_current_weather(self):
        """Test get_current_weather() function."""
        location = "Cambridge, MA, near Kendall Square"
        unit = "METRIC"
        json_string_result = get_current_weather(location=location, unit=unit)
        json_result = json.loads(json.loads(json_string_result))
        logger.info("json_result: %s", json_result)
        logger.info("type of json_result: %s", type(json_result))
        self.assertTrue(isinstance(json_result, (dict, list)))

    def test_get_current_weather2(self):
        """Test get_current_weather() function with default unit."""
        location = "Cambridge, MA, near Kendall Square"
        json_string_result = get_current_weather(location=location)
        json_result = json.loads(json.loads(json_string_result))
        logger.info("json_result: %s", json_result)
        logger.info("type of json_result: %s", type(json_result))
        self.assertTrue(isinstance(json_result, (dict, list)))

    def test_weather_tool_factory(self):
        """Test weather_tool_factory() function."""

        json_result = weather_tool_factory()
        self.assertIsInstance(json_result, dict)
