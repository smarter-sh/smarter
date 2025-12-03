"""
This module provides weather-related functions for use with the OpenAI API function calling feature.
This is a functioning implementation of the get_weather function described in the OpenAI documentation:
https://platform.openai.com/docs/guides/function-calling

Overview
--------
The main purpose of this module is to enable retrieval of current weather data and 24-hour forecasts for a given location, suitable for integration with LLM function calling. It leverages external APIs for geocoding and weather data, and includes reliability, caching, and logging features.

Features
--------
- Converts user-supplied location strings into geographic coordinates using the Google Maps Geocoding API.
- Fetches hourly temperature and precipitation data from the Open-Meteo API for the specified location.
- Returns weather data in either metric (Celsius, millimeters) or US customary units (Fahrenheit, inches).
- Caches weather API responses for one hour to reduce redundant requests.
- Retries failed requests automatically to improve reliability.
- Emits custom signals when tools are presented, requested, and responded to, for integration with other system components.
- Logging is controlled via a Waffle switch and respects the configured log level.
- Handles errors gracefully, including missing or invalid API keys and API errors.

API Integrations
----------------
- **Google Maps Geocoding API**: Used for geocoding location names to latitude and longitude.
  - Documentation: https://developers.google.com/maps/documentation/geocoding/overview
  - Python package: https://pypi.org/project/googlemaps/
  - GitHub: https://github.com/googlemaps/google-maps-services-python

- **Open-Meteo API**: Used for fetching hourly weather data.
  - Documentation: https://open-meteo.com/en/docs
  - Python package: https://pypi.org/project/openmeteo-requests/

Dependencies
------------
- googlemaps
- openmeteo_requests
- pandas
- requests_cache
- retry_requests

Configuration
-------------
Requires a valid Google Maps API key set in the environment variable `GOOGLE_MAPS_API_KEY`.

Signals
-------
- `llm_tool_presented`

See individual function documentation for usage details.
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

from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from ..signals import llm_tool_presented, llm_tool_requested, llm_tool_responded


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


# Google Maps API key
gmaps = None
try:
    if not smarter_settings.google_maps_api_key:
        raise SmarterConfigurationError(
            "Google Maps API key is not set. Please set GOOGLE_MAPS_API_KEY in your .env file."
        )
    gmaps = googlemaps.Client(key=smarter_settings.google_maps_api_key.get_secret_value())
# pylint: disable=broad-exception-caught
except ValueError as value_error:
    logger.error(
        "Could not initialize Google Maps API. Setup the Google Geolocation API service: https://developers.google.com/maps/documentation/geolocation/overview. Add your GOOGLE_MAPS_API_KEY to .env: %s"
    )

# Make sure all required weather variables are listed here
# The order of variables in hourly or daily is important to assign them correctly below
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_API_CACHE_SESSION = requests_cache.CachedSession("/tmp/.cache", expire_after=3600)  # nosec
WEATHER_API_RETRY_SESSION = retry(WEATHER_API_CACHE_SESSION, retries=5, backoff_factor=0.2)

openmeteo = openmeteo_requests.Client(session=WEATHER_API_RETRY_SESSION)


# pylint: disable=too-many-locals
def get_current_weather(tool_call: ChatCompletionMessageToolCall, location, unit="METRIC") -> str:
    """
    Retrieves the current weather and a 24-hour forecast for a specified location.

    This function uses the Google Maps Geocoding API to convert a user-supplied location string
    (such as a city and state) into geographic coordinates (latitude and longitude). It then
    queries the Open-Meteo API to obtain hourly temperature and precipitation data for the next
    24 hours at the resolved location.

    Weather data can be returned in either metric units (Celsius, millimeters) or US customary
    units (Fahrenheit, inches), depending on the `unit` parameter.

    The function emits signals to indicate when a tool is requested and when a response is sent,
    enabling integration with other system components. Logging is performed according to the
    configured log level and Waffle switch.

    If the Google Maps API key is missing or invalid, or if an error occurs during geocoding,
    a descriptive error message is returned.

    Parameters
    ----------
    tool_call : ChatCompletionMessageToolCall
        The OpenAI tool call object containing metadata about the request.
    location : str
        The location for which to retrieve weather data (e.g., "San Francisco, CA").
    unit : str, optional
        The unit system for the returned weather data. Accepts "METRIC" (default) or "USCS".

    Returns
    -------
    str
        A JSON string containing the hourly weather forecast for the next 24 hours, or an error message.
    """
    llm_tool_requested.send(sender=get_current_weather, tool_call=tool_call.model_dump(), location=location, unit=unit)
    if gmaps is None:
        retval = {
            "error": "Google Maps Geolocation service is not initialized. Setup the Google Geolocation API service: https://developers.google.com/maps/documentation/geolocation/overview, and add your GOOGLE_MAPS_API_KEY to .env"
        }
        return json.dumps(retval)

    unit = unit or "METRIC"
    location = location or "Cambridge, MA, near Kendall Square"
    latitude: float = 0.0
    longitude: float = 0.0
    address: Optional[str] = None

    # use Google Maps API to get the latitude and longitude of the location
    try:
        geocode_result = gmaps.geocode(location)  # type: ignore
        latitude = geocode_result[0]["geometry"]["location"]["lat"] or 0
        longitude = geocode_result[0]["geometry"]["location"]["lng"] or 0
        address = geocode_result[0]["formatted_address"]
    except googlemaps.exceptions.ApiError as api_error:
        logger.error("Google Maps API error getting geo coordinates for %s: %s", location, api_error)
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.error("An unexpected error occurred while getting geo coordinates for %s: %s", location, e)

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ["temperature_2m", "precipitation"],
        "current": ["temperature_2m"],
    }
    responses = openmeteo.weather_api(WEATHER_API_URL, params=params)
    response = responses[0]

    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()  # type: ignore
    hourly_precipitation_2m = hourly.Variables(1).ValuesAsNumpy()  # type: ignore
    if unit.upper() == "USCS":
        hourly_temperature_2m = hourly_temperature_2m * 9 / 5 + 32
        hourly_precipitation_2m = hourly_precipitation_2m / 2.54

    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s"),  # type: ignore
            end=pd.to_datetime(hourly.TimeEnd(), unit="s"),  # type: ignore
            freq=pd.Timedelta(seconds=hourly.Interval()),  # type: ignore
            inclusive="left",
        )
    }
    hourly_data["temperature"] = hourly_temperature_2m  # type: ignore
    hourly_data["precipitation"] = hourly_precipitation_2m  # type: ignore
    hourly_dataframe = pd.DataFrame(data=hourly_data).head(24)  # Only return the first 24 hours
    hourly_dataframe["date"] = hourly_dataframe["date"].dt.strftime("%Y-%m-%d %H:%M")
    hourly_json = hourly_dataframe.to_json(orient="records")
    llm_tool_responded.send(
        sender=get_current_weather,
        tool_call=tool_call.model_dump(),
        tool_response=hourly_json,
    )
    return json.dumps(hourly_json)


def weather_tool_factory() -> dict:
    """
    Constructs and returns a JSON-compatible dictionary defining the weather tool for OpenAI LLM function calling.

    This factory function builds the tool specification required by the OpenAI API to enable function calling from language models.
    The returned dictionary describes the `get_current_weather` function, including its name, description, and parameter schema.
    The schema specifies the expected input parameters (`location` and `unit`), their types, and constraints, ensuring correct invocation
    by the LLM.

    The function also emits a signal (`llm_tool_presented`) to notify other system components that the tool definition has been presented,
    supporting integration and observability.

    The output is intended for use in OpenAI-compatible tool registration workflows, allowing LLMs to discover and call weather-related functions.

    Returns
    -------
    dict
        A dictionary containing the tool definition for `get_current_weather`, formatted for OpenAI LLM function calling.
    """
    tool = {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "unit": {"type": "string", "enum": ["METRIC", "USCS"]},
                },
                "required": ["location"],
            },
        },
    }
    llm_tool_presented.send(sender=weather_tool_factory, tool=tool)
    return tool
