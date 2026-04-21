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
from openmeteo_requests import OpenMeteoRequestsError
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

    1. Define and initialize variables to be used in the function.
    2. Check if the necessary API clients are initialized before proceeding. If not, return an error message.
    3. Parse and validate the input arguments from the tool call.
    4. Geocode the location using the Google Maps API to get latitude and longitude.
    5. Query the OpenMeteo API for current weather and hourly forecast data.
    6. Format the response as a JSON-compatible dictionary and return it.
    7. Return the result as a JSON list (to be compatible with OpenAI function calling response format).


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

    # 1.) Define, annotate and if necessary, initialize variables to be used
    # in the function.
    # -------------------------------------------------------------------------
    arguments: dict[str, Any] = (
        {}
    )  # parsed arguments from the tool call, expected to contain 'location' and optionally 'unit'.

    latitude: float = 0.0  # google maps geocoding coordinate.
    longitude: float = 0.0  # google maps geocoding coordinate.
    address: Optional[str] = None  # formatted address from google maps geocoding result.

    response: WeatherApiResponse  # response object from the OpenMeteo API client.
    hourly: Optional[VariablesWithTime]  # hourly weather data from the OpenMeteo API response.
    hourly_temperature_2m: pd.Series = pd.Series()  # hourly temperature data extracted from the OpenMeteo API response.
    hourly_precipitation_2m: pd.Series = (
        pd.Series()
    )  # hourly precipitation data extracted from the OpenMeteo API response.
    hourly_data: dict[str, pd.DatetimeIndex] = {}  # dictionary to store hourly data with datetime index.

    result: dict[str, Any] = {}  # final result dictionary to be returned.

    # 2.) Check if the necessary API clients are initialized before proceeding.
    # If not, return an error message.
    # -------------------------------------------------------------------------
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
    if openmeteo_api_client is None:
        retval = {
            "error": (
                "OpenMeteo Weather API service is unavailable. "
                "Please check the OpenMeteo API client initialization and ensure the service is reachable."
            )
        }
        return [retval]

    # 3.) Parse and validate input arguments, geocode location, call weather API.
    # -------------------------------------------------------------------------

    # 3a.) Parse and validate input arguments
    if tool_call and tool_call.function and tool_call.function.arguments:
        if isinstance(tool_call.function.arguments, str):
            try:
                arguments = json.loads(tool_call.function.arguments)
                logger.debug(f"{logger_prefix} Parsed arguments: {json.dumps(arguments, indent=4)}")
            except json.JSONDecodeError as e:
                logger.error(f"{logger_prefix} Error parsing arguments JSON: {e}")
                return [{"error": f"Invalid arguments JSON: {e}. Received arguments: {tool_call.function.arguments}"}]
            except Exception as e:
                msg = f"Unexpected error parsing arguments: {e}. Received arguments: {tool_call.function.arguments}"
                logger.error(f"{logger_prefix} {msg}")
                return [{"error": msg}]
        else:
            arguments = tool_call.function.arguments

    # 3b.) Validate location
    try:
        location = arguments.get(WeatherParameters.LOCATION, None)
        logger.debug(f"{logger_prefix} Extracted location: {location}")
    except (AttributeError, KeyError) as e:
        msg = (
            f"Invalid location argument received: {e}. "
            f"Received arguments: {arguments}. "
            f"Expected: {{{WeatherParameters.LOCATION}: 'city/town/area/region, "
            f"[state], [country]', {WeatherParameters.UNIT}: 'METRIC|USCS'}}"
        )
        logger.error(f"{logger_prefix} {msg}")
        return [{"error": msg}]
    except Exception as e:
        msg = f"Unexpected error processing location argument: {e}. Received arguments: {arguments}"
        logger.error(f"{logger_prefix} {msg}")
        return [{"error": msg}]

    if not location or not isinstance(location, str) or not location.strip():
        return [{"error": f"No {WeatherParameters.LOCATION} provided. Please provide a valid location string."}]

    # 3c.) Validate unit
    try:
        unit = arguments.get(WeatherParameters.UNIT, WeatherUnits.METRIC)
        logger.debug(f"{logger_prefix} Extracted unit: {unit}")
    except (AttributeError, KeyError) as e:
        msg = (
            f"Invalid unit argument received: {e}. "
            f"Received arguments: {arguments}. "
            f"Expected: {{{WeatherParameters.LOCATION}: 'city/town/area/region, "
            f"[state], [country]', {WeatherParameters.UNIT}: 'METRIC|USCS'}}"
        )
        logger.error(f"{logger_prefix} {msg}")
        return [{"error": msg}]
    except Exception as e:
        msg = f"Unexpected error processing unit argument: {e}. Received arguments: {arguments}"
        logger.error(f"{logger_prefix} {msg}")
        return [{"error": msg}]

    if unit not in WeatherUnits.all():
        return [{"error": f"Invalid {WeatherParameters.UNIT}. Supported units are: {', '.join(WeatherUnits.all())}."}]

    # Send a Django signal that the tool was requested, with the tool call data, location, and unit.
    # see: https://docs.djangoproject.com/en/6.0/topics/signals/
    llm_tool_requested.send(sender=get_current_weather, tool_call=tool_call.model_dump(), location=location, unit=unit)

    # 4.) Geocode location to get latitude and longitude
    # -------------------------------------------------------------------------
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
        msg = f"Google Maps API error geocoding location '{location}': {api_error}"
        logger.error(f"{logger_prefix} {msg}")
        return [{"error": msg}]
    except json.JSONDecodeError as e:
        msg = f"JSON decode error geocoding location '{location}': {e}"
        logger.error(f"{logger_prefix} {msg}")
        return [{"error": msg}]
    except Exception as e:
        msg = f"Unexpected error geocoding location '{location}': {e}"
        logger.error(f"{logger_prefix} {msg}")
        return [{"error": msg}]

    # 5.) Query the OpenMeteo Weather API
    # -------------------------------------------------------------------------

    # OpenMeteo API parameters for current weather and hourly forecast.
    # See API docs for details: https://open-meteo.com/en/docs#api_format
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ["temperature_2m", "precipitation"],
        "current": ["temperature_2m"],
    }

    # send the API request.
    try:
        responses = openmeteo_api_client.weather_api(WEATHER_API_URL, params=params)
    except OpenMeteoRequestsError as e:
        msg = f"OpenMeteo API error: {e}"
        logger.error(f"{logger_prefix} {msg}")
        return [{"error": msg}]
    except Exception as e:
        msg = f"Unexpected error calling OpenMeteo API: {e}"
        logger.error(f"{logger_prefix} {msg}")
        return [{"error": msg}]

    # 6.) Format the response as a JSON-compatible dictionary and return it.
    # -------------------------------------------------------------------------
    try:
        # Extract the relevant weather data, convert units if necessary, and format it for return.
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
    except (IndexError, AttributeError, TypeError, ValueError, KeyError) as e:
        msg = f"Error processing weather data: {e}"
        logger.error(f"{logger_prefix} {msg}")
        return [{"error": msg}]
    except Exception as e:
        msg = f"Unexpected error processing weather data: {e}"
        logger.error(f"{logger_prefix} {msg}")
        return [{"error": msg}]

    # Send a Django signal that the tool has generated a response, with the tool call data and the response.
    # see: https://docs.djangoproject.com/en/6.0/topics/signals/
    llm_tool_responded.send(
        sender=get_current_weather,
        tool_call=tool_call.model_dump(),
        tool_response=result,
    )

    # 7.) Return the result as a JSON list (to be compatible with OpenAI function calling response format).
    # -------------------------------------------------------------------------
    return [result]


def weather_tool_factory() -> dict[str, Any]:
    """
    Constructs and returns a JSON-compatible dictionary defining the weather tool for OpenAI LLM function calling.

    Returns
    -------
    dict[str, Any]
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
