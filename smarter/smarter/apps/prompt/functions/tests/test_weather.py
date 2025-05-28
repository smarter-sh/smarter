"""
Test mixins for the plugin module.
"""

import json
from logging import getLogger

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..function_weather import get_current_weather, weather_tool_factory


logger = getLogger(__name__)


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
