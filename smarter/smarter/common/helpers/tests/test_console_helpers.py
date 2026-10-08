"""Test console helper functions."""

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..console_helpers import SmarterFormattedTextColorCodes, formatted_banner


class TestConsoleHelpers(SmarterTestBase):
    """Test console helper functions."""

    def test_formatted_banner(self):
        """Test that a banner frames its title and lines with rules, in color."""
        banner = formatted_banner("A title", "line one", "line two")
        self.assertTrue(banner.startswith(SmarterFormattedTextColorCodes.DEFAULT))
        self.assertTrue(banner.endswith(SmarterFormattedTextColorCodes.RESET))
        lines = banner.split("\n")
        self.assertEqual(lines[1], "=" * 80)
        self.assertEqual(lines[2:5], ["A title", "line one", "line two"])
        self.assertTrue(lines[5].startswith("=" * 80))

    def test_formatted_banner_color(self):
        banner = formatted_banner("A title", color_code=SmarterFormattedTextColorCodes.BRIGHT_GREEN)
        self.assertTrue(banner.startswith(SmarterFormattedTextColorCodes.BRIGHT_GREEN))
        self.assertIn("A title", banner)
