"""Test the Smarter Waffle Switch."""

from unittest.mock import MagicMock, patch

from smarter.lib.unittest.base_classes import SmarterTestBase

from .. import waffle


class TestSwitchIsActive(SmarterTestBase):
    """Test the switch_is_active function."""

    @patch("smarter.lib.django.waffle.waffle_orig")
    @patch("smarter.lib.django.waffle.cache")
    def test_switch_is_active_false(self, mock_cache: MagicMock, mock_waffle_orig: MagicMock):
        # Simulate cache miss, then switch is inactive
        mock_cache.get.return_value = None
        mock_switch = MagicMock()
        mock_switch.is_active.return_value = False
        mock_waffle_orig.get_waffle_switch_model.return_value.get.return_value = mock_switch

        result = waffle.switch_is_active("my_switch")
        self.assertFalse(result)
        mock_cache.set.assert_called()

    @patch("smarter.lib.django.waffle.waffle_orig")
    @patch("smarter.lib.django.waffle.cache")
    def test_switch_is_active_operational_error(self, mock_cache: MagicMock, mock_waffle_orig: MagicMock):
        # Simulate OperationalError
        mock_cache.get.return_value = None
        mock_waffle_orig.get_waffle_switch_model.return_value.get.side_effect = Exception("db error")

        result = waffle.switch_is_active("my_switch")
        self.assertFalse(result)
        mock_cache.set.assert_called()

    @patch("smarter.lib.django.waffle.cache")
    def test_switch_is_active_cache_hit(self, mock_cache: MagicMock):
        # Simulate cache hit
        mock_cache.get.return_value = True
        result = waffle.switch_is_active("my_switch")
        self.assertTrue(result)
        mock_cache.set.assert_not_called()
