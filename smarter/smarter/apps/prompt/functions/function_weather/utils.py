"""
Utility functions and shared resources for prompt functions, such as.

API clients and logging configuration. This module contains
code initialization and housekeeping logic that distracts from
in-classroom presentations, so we keep it here in order to keep
the main function code cleaner and easier to understand for students.

Exported functions and variables:

- google_maps_client: An authenticated Google Maps client instance, or None if initialization failed.
- should_log: A lambda function that checks if logging should be enabled based on a waffle switch.
- openmeteo_api_client: An authenticated OpenMeteo API client instance, or None if initialization failed.
"""

from typing import Optional

import googlemaps
import openmeteo_requests
import requests_cache
from django_redis import get_redis_connection
from retry_requests import retry

from smarter.apps.provider.utils import get_google_maps_api_key
from smarter.common.helpers.console_helpers import formatted_banner, formatted_text
from smarter.lib import logging
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


# OpenMeteo API client initialization with caching and retry logic.
# -----------------------------------------------------------------------------


# 1.) Initialize a Redis cache singleton for the OpenMeteo API client session
# object to reuse across function calls to avoid creating multiple sessions
# and Redis connections.
def get_session():
    """Returns a cached session for making HTTP requests, using Redis as the backend."""
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

# 2.) Wrap the session with retry logic to handle transient errors when making
# API calls. We use the retry_requests library to automatically retry failed
# requests with exponential backoff.
cached_session_with_retry = retry(redis_session, retries=5, backoff_factor=0.2)

# 3.) Initialize the OpenMeteo API client with the cached session that has retry
# logic.
openmeteo_api_client = openmeteo_requests.Client(session=cached_session_with_retry)  # type: ignore


# Google Maps API key and client
# -----------------------------------------------------------------------------
def log_google_maps_unavailable(reason: str) -> None:
    """
    Log, with instructions, that get_current_weather() cannot geocode a location.

    :param reason: Why the Google Maps client is unavailable.
    """
    base_logger.error(
        formatted_banner(
            f"[GOOGLE MAPS UNAVAILABLE] {reason}",
            "The get_current_weather() function needs a Google Maps API key to find a location.",
            "To enable it, add your key to .env, restart the platform, and run:",
            "",
            "    SMARTER_GOOGLE_MAPS_API_KEY=<your key>",
            "    docker exec smarter-app python manage.py initialize_providers",
            "",
            "Get a key at https://developers.google.com/maps/documentation/geocoding/get-api-key",
        )
    )


def get_google_maps_client() -> Optional[googlemaps.Client]:
    """
    Returns an authenticated Google Maps client instance, or None if initialization failed.

    Without an API key, or with an invalid one, it logs how to set one and returns None, so
    that get_current_weather() returns an error to the LLM rather than raising.
    """

    google_maps_api_key = get_google_maps_api_key()
    if not google_maps_api_key:
        log_google_maps_unavailable("The Google Maps API key is not set.")
        return None
    try:
        return googlemaps.Client(key=google_maps_api_key)
    except ValueError as e:
        # googlemaps rejects a key that is not a Google API key, e.g. a placeholder.
        log_google_maps_unavailable(f"The Google Maps API key is invalid: {e}")
        return None


__all__ = ["get_google_maps_client", "should_log", "openmeteo_api_client"]
