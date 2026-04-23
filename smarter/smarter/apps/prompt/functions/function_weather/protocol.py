"""
This module provides a weather forecast function for use with Smarter's
extension of the OpenAI API function calling feature.

Secondarily, this module also serves as a template for implementing
additional tools following the same protocol, with best practices for error
handling, logging, input validation, documentation style, and examples
of commonly-used third-party libraries like Pandas, NumPy, and Pint for data
manipulation and unit conversion. These best practices include the following:

- Robust input validation using Pydantic models, with clear error messages for
  invalid inputs.
- Fully annotated function signatures with type hints for all variables,
  parameters, and return types.
- Comprehensive error handling with specific exceptions for different failure
  modes (e.g. API errors, data processing errors), and logging of error details.
- Use of a WaffleSwitchedLoggerWrapper to enable or disable logging based on a
  lambda function, allowing for dynamic control of logging without code changes.
- Detailed Sphinx-compatible docstrings for all functions and classes,
  following the NumPy style guide, including sections for Parameters, Returns,
  Raises, Examples, and See Also.
- Use of Django signals to emit events at key points in the function execution,
  allowing for extensibility and integration with other parts of the application.


See Also
--------
https://developers.openai.com/api/docs/guides/function-calling

Protocol
--------
Two functions are required for implementing this protocol:

1. A factory function that returns a JSON-compatible dictionary defining the
    tool for OpenAI LLM function calling.
2. A function that implements the desired behavior (in this case, retrieving
    weather data from an API).

The factory function (`weather_tool_factory`) is consumed by
`SmarterOpenAICompatibleChatProvider.handle_function_provided()` during the tool
registration process, which adds the tool definition to the list of available
tools for the LLM to call.

The implementation function (`get_current_weather`) is executed by
`SmarterOpenAICompatibleChatProvider.process_tool_call()` when the LLM requests
this tool following iteration #1 of the conversation.

Overview
--------
Enables retrieval of current weather data and 24-hour forecasts for a given
location, suitable for LLM function calling. Features reliability, caching,
logging, robust input validation, error handling, and strict type checking.

Dependencies
------------
* googlemaps
* openmeteo_requests
* numpy
* pint
* pandas
* requests_cache
* retry_requests

Signals
-------
* llm_tool_presented
* llm_tool_requested
* llm_tool_responded
"""

# standard Python library imports
import logging
from typing import Any, Optional

# NumPy, Pandas, Google Maps API client, and OpenMeteo SDK imports
import numpy as np
import pandas as pd
from googlemaps.exceptions import ApiError as GoogleMapsApiError
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)
from openmeteo_requests import OpenMeteoRequestsError
from openmeteo_sdk.VariablesWithTime import VariablesWithTime
from openmeteo_sdk.WeatherApiResponse import WeatherApiResponse
from pint import UnitRegistry

# Smarter platform imports
from smarter.apps.prompt.signals import (
    llm_tool_presented,
    llm_tool_requested,
    llm_tool_responded,
)
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import json
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .enum import WeatherMetrics, WeatherParameters, WeatherUnits
from .models import WeatherRequestModel

# local imports of utility functions and variables (in order of import):
# - an authenticated Google Maps client instance
# - an authenticated OpenMeteo API cacheable client instance
# - a lambda function that checks if logging should be enabled
from .utils import google_maps_client, openmeteo_api_client, should_log

WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"

base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
logger_prefix = formatted_text(__name__ + ".get_current_weather()")
ureg = UnitRegistry()


def weather_tool_factory() -> dict[str, Any]:
    """
    Constructs and returns a JSON-compatible dictionary defining the weather
    tool for OpenAI LLM function calling.

    See Also
    ---------
    https://developers.openai.com/api/docs/guides/function-calling

    Django Signals
    --------------
    - llm_tool_presented: Sent when this functions is called.

    Returns
    -------
    dict[str, Any]
        A dictionary containing the tool definition for `get_current_weather`,
        formatted for OpenAI LLM function calling.
    """
    llm_tool_presented.send(
        sender=weather_tool_factory,
        tool={
            "name": get_current_weather.__name__,
            "description": "Get the current weather and 24-hour forecast for a given location.",
        },
    )

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
                        "description": "Unit system for weather data. Defaults to celsius if not provided.",
                    },
                },
                "required": [WeatherParameters.LOCATION],
                "additionalProperties": False,
            },
        },
    }
    return tool


def get_current_weather(tool_call: ChatCompletionMessageToolCall) -> list[dict[str, Any]]:
    """
    Retrieves the current weather and a 24-hour forecast for a specified
    location. The basic flow is:

    1. Define and initialize variables to be used in the function.
    2. Check if the necessary API clients are initialized before proceeding.
       If not, return an error message.
    3. Parse and validate the input arguments from the tool call.
    4. Geocode the location using the Google Maps API to get latitude and
       longitude.
    5. Query the OpenMeteo API for current weather and hourly forecast data.
    6. Format the response as a JSON-compatible dictionary and return it.
    7. Return the result as a JSON list (to be compatible with OpenAI function
       calling response format).

    Parameters
    ----------
    tool_call : ChatCompletionMessageToolCall
        The OpenAI tool call object containing metadata about the request.

    Django Signals
    --------------
    - llm_tool_requested: Sent when the tool is called, with the tool call
      data, location, and unit.
    - llm_tool_responded: Sent after the tool has generated a response, with
      the tool call data and the response.

    Returns
    -------
    list
        A JSON list containing the weather data or error message.
    """

    # -------------------------------------------------------------------------
    # 1.) Define, annotate and if necessary, initialize variables to be used
    # in the function.
    # -------------------------------------------------------------------------

    # google maps geocoding coordinates
    latitude: float = 0.0
    longitude: float = 0.0
    address: Optional[str] = None

    # response object from the OpenMeteo API client.
    response: WeatherApiResponse

    # hourly weather data variables extracted from the OpenMeteo API response
    # and packaged into a pandas DataFrame for easier manipulation and formatting.
    hourly: Optional[VariablesWithTime]
    hourly_temperature_2m: pd.Series = pd.Series()
    hourly_precipitation_2m: pd.Series = pd.Series()

    # dictionary to store hourly data with datetime index.
    hourly_data: dict[str, pd.Series | np.ndarray | pd.DatetimeIndex] = {}

    # final result dictionary to be returned.
    result: dict[str, Any] = {}

    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # 3.) Parse and validate input arguments, geocode location, call weather API.
    # -------------------------------------------------------------------------

    # 3a.) Parse and validate input arguments
    if not tool_call or not tool_call.function or not tool_call.function.arguments:
        return [{"error": "No arguments provided. Please provide a location and optionally a unit."}]

    try:
        raw_args = tool_call.function.arguments
        if isinstance(raw_args, str):
            raw_args = json.loads(raw_args)

        # Use the WeatherRequestModel Pydantic model to validate and parse the
        # input arguments.
        request = WeatherRequestModel(**raw_args)

        location = request.location
        unit = request.unit or WeatherUnits.METRIC
        logger.debug(f"{logger_prefix} Extracted location: {location}")
    # pylint: disable=broad-exception-caught
    except Exception as e:
        return [{"error": f"Invalid arguments: {e}"}]

    # 3c.) Validate unit
    if unit not in WeatherUnits.all():
        return [{"error": f"Invalid {WeatherParameters.UNIT}. Supported units are: {', '.join(WeatherUnits.all())}."}]
    logger.debug(f"{logger_prefix} Extracted unit: {unit}")

    # Send a Django signal that the tool was requested, with the tool call data, location, and unit.
    # see: https://docs.djangoproject.com/en/6.0/topics/signals/
    llm_tool_requested.send(sender=get_current_weather, tool_call=tool_call.model_dump(), location=location, unit=unit)

    # -------------------------------------------------------------------------
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
    # pylint: disable=broad-exception-caught
    except Exception as e:
        msg = f"Unexpected error geocoding location '{location}': {e}"
        logger.error(f"{logger_prefix} {msg}")
        return [{"error": msg}]

    # -------------------------------------------------------------------------
    # 5.) Query the OpenMeteo Weather API
    # -------------------------------------------------------------------------

    # OpenMeteo API parameters for current weather and hourly forecast.
    # See API docs for details: https://open-meteo.com/en/docs#api_format
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": WeatherMetrics.all(),
        "current": WeatherMetrics.all(),
    }

    # send the API request.
    try:
        responses = openmeteo_api_client.weather_api(WEATHER_API_URL, params=params)
    except OpenMeteoRequestsError as e:
        msg = f"OpenMeteo API error: {e}"
        logger.error(f"{logger_prefix} {msg}")
        return [{"error": msg}]
    # pylint: disable=broad-exception-caught
    except Exception as e:
        msg = f"Unexpected error calling OpenMeteo API: {e}"
        logger.error(f"{logger_prefix} {msg}")
        return [{"error": msg}]

    # -------------------------------------------------------------------------
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
        hourly_snowfall = hourly.Variables(2).ValuesAsNumpy()  # type: ignore
        hourly_weathercode = hourly.Variables(3).ValuesAsNumpy()  # type: ignore
        hourly_windspeed_10m = hourly.Variables(4).ValuesAsNumpy()  # type: ignore
        hourly_winddirection_10m = hourly.Variables(5).ValuesAsNumpy()  # type: ignore
        hourly_windgusts_10m = hourly.Variables(6).ValuesAsNumpy()  # type: ignore
        hourly_cloudcover = hourly.Variables(7).ValuesAsNumpy()  # type: ignore

        # Convert units if necessary - OpenMeteo returns metric by default, so convert to USCS if requested.
        if unit == WeatherUnits.USCS:

            def convert_array(arr, from_unit, to_unit):
                return pd.Series((arr * ureg(from_unit)).to(to_unit).magnitude)

            hourly_temperature_2m = convert_array(hourly_temperature_2m, "degC", "degF")
            hourly_precipitation_2m = convert_array(hourly_precipitation_2m, "millimeter", "inch")
            hourly_snowfall = convert_array(hourly_snowfall, "millimeter", "inch")
            hourly_windspeed_10m = convert_array(hourly_windspeed_10m, "kilometer/hour", "mile/hour")
            hourly_windgusts_10m = convert_array(hourly_windgusts_10m, "kilometer/hour", "mile/hour")

        hourly_data["date"] = pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s"),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s"),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        )
        hourly_data[WeatherMetrics.TEMPERATURE_2M] = hourly_temperature_2m
        hourly_data[WeatherMetrics.PRECIPITATION] = hourly_precipitation_2m
        hourly_data[WeatherMetrics.SNOWFALL] = hourly_snowfall
        hourly_data[WeatherMetrics.WEATHERCODE] = hourly_weathercode
        hourly_data[WeatherMetrics.WINDSPEED_10M] = hourly_windspeed_10m
        hourly_data[WeatherMetrics.WINDDIRECTION_10M] = hourly_winddirection_10m
        hourly_data[WeatherMetrics.WINDGUSTS_10M] = hourly_windgusts_10m
        hourly_data[WeatherMetrics.CLOUDCOVER] = hourly_cloudcover

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
    # pylint: disable=broad-exception-caught
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

    # -------------------------------------------------------------------------
    # 7.) Return the result as a JSON list (to be compatible with OpenAI
    # function calling response format).
    # -------------------------------------------------------------------------
    return [result]
