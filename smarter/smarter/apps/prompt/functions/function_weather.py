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
from typing import Any, Optional

import pandas as pd
from googlemaps.exceptions import ApiError as GoogleMapsApiError
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)
from openmeteo_sdk.VariablesWithTime import VariablesWithTime
from openmeteo_sdk.WeatherApiResponse import WeatherApiResponse

from smarter.apps.prompt.signals import llm_tool_requested, llm_tool_responded
from smarter.common.enum import SmarterEnum
from smarter.common.exceptions import SmarterException
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import json  # for robust JSON parsing of tool call arguments
from smarter.lib.logging import (
    WaffleSwitchedLoggerWrapper,  # to control logging output based on a waffle switch
)

from .utils import (
    google_maps_client,  # an authenticated Google Maps client instance, or None if initialization failed
)
from .utils import (
    openmeteo_api_client,  # an authenticated OpenMeteo API client instance, or None if initialization failed
)
from .utils import (
    should_log,  # a lambda function that checks if logging should be enabled based on a waffle switch
)

base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
logger_prefix = formatted_text(__name__ + ".get_current_weather()")


WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"


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


class WeatherError(SmarterException):
    """Custom exception for weather tool errors."""


def get_current_weather(tool_call: ChatCompletionMessageToolCall) -> list[dict[str, Any]]:
    """
    Retrieves the current weather and a 24-hour forecast for a specified location.
    The basic flow is:

    1. Parse and validate the input arguments from the tool call.
    2. Geocode the location using the Google Maps API to get latitude and longitude.
    3. Query the OpenMeteo API for current weather and hourly forecast data.
    4. Format the response as a JSON-compatible dictionary and return it.
    5. Return the result as a JSON list (to be compatible with OpenAI function calling response format).


    Parameters
    ----------
    tool_call : ChatCompletionMessageToolCall
        The OpenAI tool call object containing metadata about the request.

    Django Signals
    --------------
    - llm_tool_requested: Sent when the tool is called, with the tool call data, location, and unit.
    - llm_tool_responded: Sent after the tool has generated a response, with the tool call data and the response.

    Returns
    -------
    list
        A JSON list containing the weather data or error message.
    """
    latitude: float = 0.0
    longitude: float = 0.0
    address: Optional[str] = None
    arguments: dict[str, Any] = {}
    response: WeatherApiResponse
    hourly: Optional[VariablesWithTime]
    hourly_data: dict[str, pd.DatetimeIndex]
    result: dict[str, Any]

    if google_maps_client is None:
        retval = {
            "error": (
                "Google Maps Geolocation service is unavailable. "
                "Setup the Google Geolocation API service: "
                "https://developers.google.com/maps/documentation/geolocation/overview, "
                "and add your GOOGLE_MAPS_API_KEY to .env"
            )
        }
        return [retval]

    # 1a.) Parse and validate input arguments
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

    # 1b.) Validate location
    try:
        location = arguments.get(WeatherParameters.LOCATION, None)
        logger.debug(f"{logger_prefix} Extracted location: {location}")
    except (AttributeError, KeyError) as e:
        logger.error(f"{logger_prefix} Unexpected error processing location argument: {arguments} Exception: {e}")
        return [
            {
                "error": (
                    f"Unexpected error processing arguments: {e}. "
                    f"Received arguments: {arguments}. "
                    f"Expected: {{'{WeatherParameters.LOCATION}': 'city, state', "
                    f"'{WeatherParameters.UNIT}': 'METRIC|USCS'}}"
                )
            }
        ]

    if not location or not isinstance(location, str) or not location.strip():
        return [{"error": f"No {WeatherParameters.LOCATION} provided. Please provide a valid location string."}]

    # 1c.) Validate unit
    try:
        unit = arguments.get(WeatherParameters.UNIT, WeatherUnits.METRIC)
        logger.debug(f"{logger_prefix} Extracted unit: {unit}")
    except (AttributeError, KeyError) as e:
        logger.error(f"{logger_prefix} Unexpected error processing unit argument: {arguments} Exception: {e}")
        return [
            {
                "error": (
                    f"Unexpected error processing arguments: {e}. "
                    f"Received arguments: {arguments}. "
                    f"Expected: {{'{WeatherParameters.LOCATION}': 'city, state', "
                    f"'{WeatherParameters.UNIT}': 'METRIC|USCS'}}"
                )
            }
        ]

    if unit not in WeatherUnits.all():
        return [{"error": f"Invalid {WeatherParameters.UNIT}. Supported units are: {', '.join(WeatherUnits.all())}."}]

    # Send a Django signal that the tool was requested, with the tool call data, location, and unit.
    llm_tool_requested.send(sender=get_current_weather, tool_call=tool_call.model_dump(), location=location, unit=unit)

    # 2.) Geocode location to get latitude and longitude
    try:
        # Use the Google Maps API client to geocode the location string into
        # latitude and longitude coordinates.
        geocode_result = google_maps_client.geocode(location)  # type: ignore
        if not geocode_result or "geometry" not in geocode_result[0] or "location" not in geocode_result[0]["geometry"]:
            logger.error(f"{logger_prefix} Geocoding failed for location: {location}")
            return [{"error": f"Could not geocode location: {location}"}]

        # Extract latitude and longitude from the geocoding result, with
        # fallbacks to 0 if not found.
        latitude = geocode_result[0]["geometry"]["location"]["lat"] or 0
        longitude = geocode_result[0]["geometry"]["location"]["lng"] or 0

        # Extract the formatted address from the geocoding result, with a
        # fallback to the original location string if not found.
        address = geocode_result[0].get("formatted_address", location)
    except GoogleMapsApiError as api_error:
        logger.error(f"{logger_prefix} Google Maps API error getting geo coordinates for {location}: {api_error}")
        return [{"error": f"Google Maps API error: {api_error}"}]
    except Exception as e:
        logger.error(f"{logger_prefix} Unexpected error getting geo coordinates for {location}: {e}")
        return [{"error": f"Unexpected error geocoding location: {e}"}]

    # 3.) Query the OpenMeteo Weather API
    try:

        # OpenMeteo API parameters for current weather and hourly forecast.
        # See API docs for details: https://open-meteo.com/en/docs#api_format
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ["temperature_2m", "precipitation"],
            "current": ["temperature_2m"],
        }

        # send the API request.
        responses = openmeteo_api_client.weather_api(WEATHER_API_URL, params=params)
        response = responses[0]
        hourly = response.Hourly()
        if not hourly:
            logger.error(f"{logger_prefix} Weather API response missing hourly data for location: {location}")
            return [{"error": f"Weather API response missing hourly data for location: {location}"}]
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()  # type: ignore
        hourly_precipitation_2m = hourly.Variables(1).ValuesAsNumpy()  # type: ignore

        # Convert units if necessary - OpenMeteo returns metric by default, so convert to USCS if requested.
        if unit == WeatherUnits.USCS:
            hourly_temperature_2m = hourly_temperature_2m * 9 / 5 + 32
            hourly_precipitation_2m = hourly_precipitation_2m / 2.54

        # 4.) Format the response as a JSON-compatible dictionary and return it.
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

        # Construct the final result dictionary to return.
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

    # Send a Django signal that the tool has generated a response, with the tool call data and the response.
    llm_tool_responded.send(
        sender=get_current_weather,
        tool_call=tool_call.model_dump(),
        tool_response=result,
    )

    # 5.) Return the result as a JSON list (to be compatible with OpenAI function calling response format).
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
