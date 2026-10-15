Testing an Extension
====================

An Extension's tests live in its repository's ``tests/`` directory, beside its package. They call
its tools directly, with the settings they need, without installing the Extension, without the
database, and without an LLM.

Testing a Tool
--------------

:mod:`smarter.apps.llmtool.extension.testing` has two helpers:

- :func:`~smarter.apps.llmtool.extension.testing.tool_context` returns a tool call's context, with
  the settings you give it.
- :func:`~smarter.apps.llmtool.extension.testing.call_tool` calls a tool as the platform does: it
  validates the arguments, and returns an
  :class:`~smarter.apps.llmtool.extension.protocol.ExtensionToolError`, or invalid arguments, as
  ``{"error": ...}``. Unlike the platform, it lets any other exception propagate, so that your test
  sees it.

Mock the third-party services, so that the tests are fast and need no API keys:

.. code-block:: python
    :caption: tests/test_tools.py

    """Tests of the get_weather tool."""

    import unittest
    from unittest.mock import patch

    from pydantic import SecretStr

    from smarter.apps.llmtool.extension.testing import call_tool, tool_context
    from weather.models import Conditions
    from weather.services import Place, Weather
    from weather.tools import GetWeather

    CONTEXT = tool_context(
        "weather",
        google_maps_api_key=SecretStr("test-key"),
        weather_api_url="https://api.open-meteo.com/v1/forecast",
    )


    class TestGetWeather(unittest.TestCase):
        """Test get_weather, with its services mocked."""

        def test_weather(self):
            now = Conditions(time="2026-10-15 14:00", temperature=18.5, precipitation=0, wind_speed=12, cloud_cover=40)
            found = Weather(timezone="Europe/Paris", current=now, forecast=[now])
            with patch("weather.tools.geocode", return_value=Place("Paris, France", 48.85, 2.35)), patch(
                "weather.tools.weather", return_value=found
            ):
                result = call_tool(GetWeather, {"location": "Paris"}, CONTEXT)
            self.assertEqual(result["location"], "Paris, France")
            self.assertEqual(result["units"]["wind_speed"], "km/h")

        def test_unknown_place(self):
            with patch("weather.services.googlemaps.Client") as client:
                client.return_value.geocode.return_value = []
                result = call_tool(GetWeather, {"location": "Atlantis"}, CONTEXT)
            self.assertIn("Could not find Atlantis", result["error"])

        def test_invalid_arguments(self):
            self.assertIn("Invalid arguments", call_tool(GetWeather, {"unit": "KELVIN"})["error"])

Running the Tests
-----------------

An Extension's tests import Smarter, so they run in a Smarter development container, where
``manage.py test_extension`` puts the repository on ``sys.path`` and runs its ``tests/``:

.. code-block:: console

    docker cp ../smarter-extension-weather smarter-app:/tmp/
    docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py test_extension /tmp/smarter-extension-weather"

Before you publish, also check the packaged Extension as the installer will, with
``manage.py validate_extension``, and install it on your development platform to try it with an
LLM. See :doc:`developer-guide`.
