"""Test get_current_weather() with the Google Maps and OpenMeteo clients mocked."""

from unittest.mock import MagicMock, patch

import numpy as np
from googlemaps.exceptions import ApiError as GoogleMapsApiError
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)

from smarter.lib import json
from smarter.lib.unittest.base_classes import SmarterTestBase

from ..function_weather.protocol import OpenMeteoRequestsError, get_current_weather

MODULE = "smarter.apps.prompt.functions.function_weather.protocol"
HOURS = 48


def tool_call(arguments: str = '{"location": "Cambridge, MA"}') -> ChatCompletionMessageToolCall:
    """Return a get_current_weather tool call with the given arguments."""
    function = Function(name="get_current_weather", arguments=arguments)
    return ChatCompletionMessageToolCall(id="test_weather_protocol", function=function, type="function")


def geocode_result(lat: float = 42.36, lng: float = -71.08) -> list[dict]:
    """Return a Google Maps geocode() result."""
    return [{"geometry": {"location": {"lat": lat, "lng": lng}}, "formatted_address": "Cambridge, MA, USA"}]


def weather_responses(hourly=True) -> list[MagicMock]:
    """Return an OpenMeteo weather_api() result holding ``HOURS`` hours of data."""
    response = MagicMock()
    if not hourly:
        response.Hourly.return_value = None
        return [response]
    variables = MagicMock()
    variables.ValuesAsNumpy.return_value = np.arange(HOURS, dtype=float)
    hourly_data = MagicMock()
    hourly_data.Variables.return_value = variables
    hourly_data.Time.return_value = 0
    hourly_data.TimeEnd.return_value = HOURS * 3600
    hourly_data.Interval.return_value = 3600
    response.Hourly.return_value = hourly_data
    return [response]


class TestGetCurrentWeatherProtocol(SmarterTestBase):
    """Test every branch of get_current_weather() without calling the real APIs."""

    def setUp(self):
        super().setUp()
        self.google_maps_client = MagicMock()
        self.google_maps_client.geocode.return_value = geocode_result()
        self.openmeteo_api_client = MagicMock()
        self.openmeteo_api_client.weather_api.return_value = weather_responses()
        for target, value in (
            ("get_google_maps_client", MagicMock(return_value=self.google_maps_client)),
            ("openmeteo_api_client", self.openmeteo_api_client),
        ):
            patcher = patch(f"{MODULE}.{target}", value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def assertError(self, result: list, text: str):
        """Assert that the result is a single error that contains text."""
        self.assertEqual(len(result), 1)
        self.assertIn("error", result[0])
        self.assertIn(text, result[0]["error"])

    def test_metric_forecast(self):
        """A metric forecast holds 24 hours of data and the geocoded address."""
        result = get_current_weather(tool_call('{"location": "Cambridge, MA", "unit": "METRIC"}'))
        self.assertEqual(len(result), 1)
        forecast = result[0]
        self.assertEqual(forecast["location"], "Cambridge, MA, USA")
        self.assertEqual(forecast["unit"], "METRIC")
        self.assertEqual(len(forecast["forecast"]), 24)
        self.assertEqual(forecast["forecast"][1]["temperature_2m"], 1.0)
        self.assertEqual(forecast["forecast"][0]["date"], "1970-01-01 00:00")
        self.assertIsInstance(json.dumps(result), str)

    def test_default_unit_is_metric(self):
        """With no unit, the forecast is metric."""
        result = get_current_weather(tool_call())
        self.assertEqual(result[0]["unit"], "METRIC")

    def test_uscs_forecast_is_converted(self):
        """A USCS forecast converts Celsius to Fahrenheit."""
        result = get_current_weather(tool_call('{"location": "Cambridge, MA", "unit": "USCS"}'))
        forecast = result[0]["forecast"]
        self.assertEqual(result[0]["unit"], "USCS")
        self.assertAlmostEqual(forecast[0]["temperature_2m"], 32.0)
        self.assertAlmostEqual(forecast[10]["temperature_2m"], 50.0)

    def test_dict_arguments(self):
        """Arguments that are already a dict are accepted."""
        call = MagicMock()
        call.function.arguments = {"location": "Cambridge, MA"}
        call.model_dump.return_value = {}
        result = get_current_weather(call)
        self.assertEqual(result[0]["location"], "Cambridge, MA, USA")

    def test_google_maps_unavailable(self):
        """Without a Google Maps client, an error is returned."""
        with patch(f"{MODULE}.get_google_maps_client", return_value=None):
            self.assertError(get_current_weather(tool_call()), "Google Maps")

    def test_openmeteo_unavailable(self):
        """Without an OpenMeteo client, an error is returned."""
        with patch(f"{MODULE}.openmeteo_api_client", None):
            self.assertError(get_current_weather(tool_call()), "OpenMeteo")

    def test_no_arguments(self):
        """A tool call without arguments returns an error."""
        self.assertError(get_current_weather(tool_call("")), "No arguments provided")

    def test_invalid_arguments(self):
        """Arguments that fail validation return an error."""
        self.assertError(get_current_weather(tool_call('{"location": "  "}')), "Invalid arguments")
        self.assertError(get_current_weather(tool_call('{"location": "x", "unit": "kelvin"}')), "Invalid arguments")
        self.assertError(get_current_weather(tool_call("not json")), "Invalid arguments")

    def test_unsupported_unit(self):
        """A unit that passes validation but isn't a WeatherUnits value returns an error."""
        request = MagicMock(location="Cambridge, MA", unit="kelvin")
        with patch(f"{MODULE}.WeatherRequestModel", return_value=request):
            self.assertError(get_current_weather(tool_call()), "Supported units are")

    def test_geocode_finds_nothing(self):
        """A location that can't be geocoded returns an error."""
        self.google_maps_client.geocode.return_value = []
        self.assertError(get_current_weather(tool_call()), "Could not geocode location")

    def test_geocode_api_error(self):
        """A Google Maps API error returns an error."""
        self.google_maps_client.geocode.side_effect = GoogleMapsApiError("REQUEST_DENIED", "bad key")
        self.assertError(get_current_weather(tool_call()), "Google Maps API error")

    def test_geocode_json_error(self):
        """A JSON decode error from Google Maps returns an error."""
        self.google_maps_client.geocode.side_effect = json.JSONDecodeError("bad", "doc", 0)
        self.assertError(get_current_weather(tool_call()), "JSON decode error")

    def test_geocode_unexpected_error(self):
        """Any other geocoding error returns an error."""
        self.google_maps_client.geocode.side_effect = RuntimeError("boom")
        self.assertError(get_current_weather(tool_call()), "Unexpected error geocoding")

    def test_openmeteo_api_error(self):
        """An OpenMeteo API error returns an error."""
        self.openmeteo_api_client.weather_api.side_effect = OpenMeteoRequestsError("down")
        self.assertError(get_current_weather(tool_call()), "OpenMeteo API error")

    def test_openmeteo_unexpected_error(self):
        """Any other OpenMeteo error returns an error."""
        self.openmeteo_api_client.weather_api.side_effect = RuntimeError("boom")
        self.assertError(get_current_weather(tool_call()), "Unexpected error calling OpenMeteo")

    def test_missing_hourly_data(self):
        """A weather response without hourly data returns an error."""
        self.openmeteo_api_client.weather_api.return_value = weather_responses(hourly=False)
        self.assertError(get_current_weather(tool_call()), "missing hourly data")

    def test_empty_weather_response(self):
        """An empty weather response returns a processing error."""
        self.openmeteo_api_client.weather_api.return_value = []
        self.assertError(get_current_weather(tool_call()), "Error processing weather data")

    def test_unexpected_processing_error(self):
        """Any other processing error returns an error."""
        response = MagicMock()
        response.Hourly.side_effect = RuntimeError("boom")
        self.openmeteo_api_client.weather_api.return_value = [response]
        self.assertError(get_current_weather(tool_call()), "Unexpected error processing weather data")
