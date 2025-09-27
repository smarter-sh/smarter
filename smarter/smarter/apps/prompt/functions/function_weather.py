"""
OpenAI API example function: https://platform.openai.com/docs/guides/function-calling
This function returns the current weather in a given location as a 24-hour forecast.
The function is called by the OpenAI API and returns a JSON object.

Geocoding: Google Maps API
Documentation:
- https://developers.google.com/maps/documentation/geocoding/overview
- https://pypi.org/project/googlemaps/
- https://github.com/googlemaps/google-maps-services-python


Open-Meteo API:
Documentation:  https://open-meteo.com/en/docs
                https://pypi.org/project/openmeteo-requests/

The Open-Meteo API is used to get the weather data. The API is rate-limited to 1 request per second. It is called with the
openmeteo_requests Python package, which is a wrapper for the requests package. It is used to cache the API responses
to avoid repeated API calls, and to retry failed API calls.
"""

import json
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

from smarter.common.conf import settings
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from ..signals import llm_tool_presented, llm_tool_requested, llm_tool_responded


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


# Google Maps API key
gmaps = None
try:
    if not settings.google_maps_api_key:
        raise SmarterConfigurationError(
            "Google Maps API key is not set. Please set GOOGLE_MAPS_API_KEY in your .env file."
        )
    gmaps = googlemaps.Client(key=settings.google_maps_api_key.get_secret_value())
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
    """Get the current weather in a given location as a 24-hour forecast"""
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
    """Return a list of tools that can be called by the OpenAI API"""
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
