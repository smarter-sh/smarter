"""Test :func:`smarter.apps.prompt.functions.function_weather.utils.get_google_maps_client`."""

from unittest.mock import patch

import googlemaps

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..function_weather import utils

MODULE = "smarter.apps.prompt.functions.function_weather.utils"


class TestGetGoogleMapsClient(SmarterTestBase):
    """Test that the Google Maps client is None, with instructions logged, rather than raised, without a valid key."""

    def test_client(self):
        with patch(f"{MODULE}.get_google_maps_api_key", return_value="AIza-test-key"):
            self.assertIsInstance(utils.get_google_maps_client(), googlemaps.Client)

    def test_without_a_key(self):
        with (
            patch(f"{MODULE}.get_google_maps_api_key", return_value=None),
            patch(f"{MODULE}.base_logger") as logger,
        ):
            self.assertIsNone(utils.get_google_maps_client())
        self.assertIn("SMARTER_GOOGLE_MAPS_API_KEY", logger.error.call_args.args[0])

    def test_with_an_invalid_key(self):
        """Googlemaps raises for a key that is not a Google API key, e.g. a placeholder."""
        with (
            patch(f"{MODULE}.get_google_maps_api_key", return_value="SET-ME-PLEASE-not-a-google-key"),
            patch(f"{MODULE}.base_logger") as logger,
        ):
            self.assertIsNone(utils.get_google_maps_client())
        self.assertIn("invalid", logger.error.call_args.args[0])
