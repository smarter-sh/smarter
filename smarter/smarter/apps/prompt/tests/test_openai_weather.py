# pylint: disable=wrong-import-position
# pylint: disable=R0801
"""Test lambda_openai_v2 function."""

import os
import sys
from pathlib import Path

from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)

# python stuff
from smarter.lib import json
from smarter.lib.unittest.base_classes import SmarterTestBase

HERE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = str(Path(HERE).parent.parent)
PYTHON_ROOT = str(Path(PROJECT_ROOT).parent)
if PYTHON_ROOT not in sys.path:
    sys.path.append(PYTHON_ROOT)  # noqa: E402


from ..functions.function_weather import get_current_weather, weather_tool_factory


class TestLambdaOpenaiFunctionWeather(SmarterTestBase):
    """Test OpenAI Function Weather."""

    # pylint: disable=broad-exception-caught
    def test_get_current_weather(self):
        """Test default return value of get_current_weather()"""
        location = "London, UK"
        unit = "METRIC"
        function = Function(
            name="get_current_weather", arguments='{"location": "Cambridge, MA, near Kendall Square", "unit": "METRIC"}'
        )
        tool_call = ChatCompletionMessageToolCall(id="test_get_current_weather", function=function, type="function")

        retval = get_current_weather(tool_call=tool_call, location=location, unit=unit)
        self.assertIsInstance(retval, list)

    def test_weather_tool_factory(self):
        """Test integrity weather_tool_factory()"""
        wtf = weather_tool_factory()
        self.assertIsInstance(wtf, dict)

        self.assertIsInstance(wtf, dict)
        self.assertTrue("type" in wtf)
        self.assertTrue("function" in wtf)
