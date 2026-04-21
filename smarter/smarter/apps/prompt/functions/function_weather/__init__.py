"""
Get the current weather in a given location and format it as a string.
"""

from .function_weather import get_current_weather, weather_tool_factory

__all__ = [
    "get_current_weather",
    "weather_tool_factory",
]
