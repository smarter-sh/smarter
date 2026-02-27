# pylint: disable=broad-exception-caught
"""
This module provides weather-related functions for use with the OpenAI API function calling feature.

Overview
--------
Enables retrieval of current weather data and 24-hour forecasts for a given location, suitable for LLM function calling.
Features reliability, caching, logging, and robust input validation.

Dependencies
------------
- googlemaps
- openmeteo_requests
- pandas
- requests_cache
- retry_requests

Signals
-------
- llm_tool_presented
- llm_tool_requested
- llm_tool_responded
"""

import logging
from typing import Optional

import googlemaps
import openmeteo_requests
import pandas as pd
import requests_cache
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)
from retry_requests import retry

from smarter.common.conf import smarter_settings
from smarter.common.enum import SmarterEnum
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from ..signals import llm_tool_requested, llm_tool_responded


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
logger_prefix = formatted_text(__name__)


# Google Maps API key and client
gmaps = None
if (
    not smarter_settings.google_maps_api_key
    or smarter_settings.google_maps_api_key.get_secret_value() == smarter_settings.default_missing_value
):
    logger.error(f"{logger_prefix} Google Maps API key is not set. Please set GOOGLE_MAPS_API_KEY in your .env file.")

try:
    gmaps = googlemaps.Client(key=smarter_settings.google_maps_api_key.get_secret_value())
except Exception as value_error:
    logger.error(
        f"{logger_prefix} Could not initialize Google Maps API. Setup the Google Geolocation API service: https://developers.google.com/maps/documentation/geolocation/overview. Add your GOOGLE_MAPS_API_KEY to .env: {value_error}"
    )

WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_API_CACHE_SESSION = requests_cache.CachedSession("/tmp/.cache", expire_after=3600)  # nosec
WEATHER_API_RETRY_SESSION = retry(WEATHER_API_CACHE_SESSION, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=WEATHER_API_RETRY_SESSION)


class WeatherParameters(SmarterEnum):
    """
    Enum for weather function parameters.
    """

    LOCATION = "location"
    UNIT = "unit"


class WeatherUnits(SmarterEnum):
    """
    Enum for supported weather units.
    """

    METRIC = "METRIC"
    USCS = "USCS"


class WeatherError(Exception):
    """Custom exception for weather tool errors."""


def get_current_weather(tool_call: ChatCompletionMessageToolCall) -> list:
    """
    Retrieves the current weather and a 24-hour forecast for a specified location.

    Parameters
    ----------
    tool_call : ChatCompletionMessageToolCall
        The OpenAI tool call object containing metadata about the request.

    Returns
    -------
    list
        A JSON-compatible list containing the weather data or error message.
    """
    # Parse arguments
    arguments = None
    if tool_call and tool_call.function and tool_call.function.arguments:
        if isinstance(tool_call.function.arguments, str):
            try:
                arguments = json.loads(tool_call.function.arguments)
                logger.debug(f"{logger_prefix} Parsed arguments: {json.dumps(arguments, indent=4)}")
            except Exception as e:
                logger.error(f"{logger_prefix} Error parsing arguments JSON: {e}")
                return [{"error": f"Invalid arguments JSON: {e}. Received arguments: {tool_call.function.arguments}"}]
        else:
            arguments = tool_call.function.arguments
    else:
        arguments = {}

    # Validate location
    try:
        location = arguments.get(WeatherParameters.LOCATION, None)
        logger.debug(f"{logger_prefix} Extracted location: {location}")
    except Exception as e:
        logger.error(f"{logger_prefix} Unexpected error processing location argument: {arguments} Exception: {e}")
        return [
            {
                "error": f"Unexpected error processing arguments: {e}. Received arguments: {arguments}. Expected: {{'{WeatherParameters.LOCATION}': 'city, state', '{WeatherParameters.UNIT}': 'METRIC|USCS'}}"
            }
        ]

    if not location or not isinstance(location, str) or not location.strip():
        return [{"error": f"No {WeatherParameters.LOCATION} provided. Please provide a valid location string."}]

    # Validate unit
    try:
        unit = arguments.get(WeatherParameters.UNIT, WeatherUnits.METRIC)
        logger.debug(f"{logger_prefix} Extracted unit: {unit}")
    except Exception as e:
        logger.error(f"{logger_prefix} Unexpected error processing unit argument: {arguments} Exception: {e}")
        return [
            {
                "error": f"Unexpected error processing arguments: {e}. Received arguments: {arguments}. Expected: {{'{WeatherParameters.LOCATION}': 'city, state', '{WeatherParameters.UNIT}': 'METRIC|USCS'}}"
            }
        ]

    if unit not in WeatherUnits.all():
        return [{"error": f"Invalid {WeatherParameters.UNIT}. Supported units are: {', '.join(WeatherUnits.all())}."}]

    llm_tool_requested.send(sender=get_current_weather, tool_call=tool_call.model_dump(), location=location, unit=unit)

    if gmaps is None:
        retval = {
            "error": "Google Maps Geolocation service is not initialized. Setup the Google Geolocation API service: https://developers.google.com/maps/documentation/geolocation/overview, and add your GOOGLE_MAPS_API_KEY to .env"
        }
        return [retval]

    latitude: float = 0.0
    longitude: float = 0.0
    address: Optional[str] = None

    # Geocode location
    try:
        geocode_result = gmaps.geocode(location)
        if not geocode_result or "geometry" not in geocode_result[0] or "location" not in geocode_result[0]["geometry"]:
            logger.error(f"{logger_prefix} Geocoding failed for location: {location}")
            return [{"error": f"Could not geocode location: {location}"}]
        latitude = geocode_result[0]["geometry"]["location"]["lat"] or 0
        longitude = geocode_result[0]["geometry"]["location"]["lng"] or 0
        address = geocode_result[0].get("formatted_address", location)
    except googlemaps.exceptions.ApiError as api_error:
        logger.error(f"{logger_prefix} Google Maps API error getting geo coordinates for {location}: {api_error}")
        return [{"error": f"Google Maps API error: {api_error}"}]
    except Exception as e:
        logger.error(f"{logger_prefix} Unexpected error getting geo coordinates for {location}: {e}")
        return [{"error": f"Unexpected error geocoding location: {e}"}]

    # Query weather API
    try:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ["temperature_2m", "precipitation"],
            "current": ["temperature_2m"],
        }
        responses = openmeteo.weather_api(WEATHER_API_URL, params=params)
        response = responses[0]
        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        hourly_precipitation_2m = hourly.Variables(1).ValuesAsNumpy()
        if unit == WeatherUnits.USCS:
            hourly_temperature_2m = hourly_temperature_2m * 9 / 5 + 32
            hourly_precipitation_2m = hourly_precipitation_2m / 2.54

        hourly_data = {
            "date": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s"),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s"),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left",
            )
        }
        hourly_data["temperature"] = hourly_temperature_2m  # type: ignore
        hourly_data["precipitation"] = hourly_precipitation_2m  # type: ignore
        hourly_dataframe = pd.DataFrame(data=hourly_data).head(24)
        hourly_dataframe["date"] = hourly_dataframe["date"].dt.strftime("%Y-%m-%d %H:%M")
        hourly_json = hourly_dataframe.to_dict(orient="records")
        result = {
            "location": address,
            "latitude": latitude,
            "longitude": longitude,
            "unit": unit,
            "forecast": hourly_json,
        }
    except Exception as e:
        logger.error(f"{logger_prefix} Error fetching weather data: {e}")
        return [{"error": f"Error fetching weather data: {e}"}]

    llm_tool_responded.send(
        sender=get_current_weather,
        tool_call=tool_call.model_dump(),
        tool_response=result,
    )
    return [result]


def weather_tool_factory() -> dict:
    """
    Constructs and returns a JSON-compatible dictionary defining the weather tool for OpenAI LLM function calling.

    Returns
    -------
    dict
        A dictionary containing the tool definition for `get_current_weather`, formatted for OpenAI LLM function calling.
    """
    tool = {
        "type": "function",
        "function": {
            "name": get_current_weather.__name__,
            "description": "Get the current weather and 24-hour forecast for a given location.",
            "parameters": {
                "type": "object",
                "properties": {
                    WeatherParameters.LOCATION: {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    WeatherParameters.UNIT: {
                        "type": "string",
                        "enum": WeatherUnits.all(),
                        "description": f"Unit system for weather data. Supported: {WeatherUnits.list_all()}",
                    },
                },
                "required": [WeatherParameters.LOCATION],
            },
        },
    }
    return tool
