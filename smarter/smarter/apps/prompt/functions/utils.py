"""
Utility functions and shared resources for prompt functions, such as
API clients and logging configuration. This module contains
code initialization and housekeeping logic that distracts from
in-classroom presentations, so we keep it here in order to keep
the main function code cleaner and easier to understand for students.

Exported functions and variables:

- google_maps_client: An authenticated Google Maps client instance, or None if initialization failed.
- should_log: A lambda function that checks if logging should be enabled based on a waffle switch.
- openmeteo_api_client: An authenticated OpenMeteo API client instance, or None if initialization failed.
"""

import logging

import googlemaps
import openmeteo_requests
import requests_cache
from django_redis import get_redis_connection
from retry_requests import retry

from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterInvalidApiKeyError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


# pylint: disable=W0613
# Lambda function to check if logging should be enabled based on a waffle switch.
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
logger_prefix = formatted_text(__name__)


# Cache singleton for the session object to reuse across function calls to
# avoid creating multiple sessions and Redis connections.
def get_session():
    """
    Returns a cached session for making HTTP requests, using Redis as the backend.
    """
    # pylint: disable=global-statement
    _session = None
    if _session is None:
        _redis_client = get_redis_connection("default")

        _session = requests_cache.CachedSession(
            backend="redis",
            connection=_redis_client,
            expire_after=300,
            key_prefix="http_cache:",
        )
    return _session


redis_session = get_session()

# Wrap the session with retry logic to handle transient errors when making API calls.
# We use the retry_requests library to automatically retry failed requests with exponential backoff.
cached_session_with_retry = retry(redis_session, retries=5, backoff_factor=0.2)

# Initialize the OpenMeteo API client with the cached session that has retry
# logic.
openmeteo_api_client = openmeteo_requests.Client(session=cached_session_with_retry)  # type: ignore


# Google Maps API key and client
google_maps_client = None
if (
    not smarter_settings.google_maps_api_key
    or smarter_settings.google_maps_api_key.get_secret_value() == smarter_settings.default_missing_value
):
    try:
        raise SmarterInvalidApiKeyError(
            f"{logger_prefix} Google Maps API key is not set. Please set GOOGLE_MAPS_API_KEY in your .env file."
        )
    except SmarterInvalidApiKeyError as invalid_key_error:
        logger.error(str(invalid_key_error))

try:
    google_maps_client = googlemaps.Client(key=smarter_settings.google_maps_api_key.get_secret_value())
# pylint: disable=broad-except
except ValueError as e:
    try:
        raise SmarterInvalidApiKeyError(
            f"{logger_prefix} Invalid Google Maps API key. Please check your GOOGLE_MAPS_API_KEY in your .env file: {e}"
        ) from e
    except SmarterInvalidApiKeyError as invalid_key_error:
        logger.error(str(invalid_key_error))
except Exception as value_error:
    logger.error(
        f"{logger_prefix} Could not initialize Google Maps API. Setup the Google Geolocation API service: https://developers.google.com/maps/documentation/geolocation/overview. Add your GOOGLE_MAPS_API_KEY to .env: {value_error}"
    )


__all__ = ["google_maps_client", "should_log", "openmeteo_api_client"]
