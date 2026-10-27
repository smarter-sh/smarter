"""Test console helper functions."""

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..console_helpers import SmarterFormattedText


class TestConsoleHelpers(SmarterTestBase):
    """Test console helper functions."""

    def test_formatted_banner(self):
        """Test that a banner frames its title and lines with rules, in color."""
        banner = SmarterFormattedText.banner("A title", "line one", "line two")
        self.assertTrue(banner.startswith(SmarterFormattedText.DEFAULT))
        self.assertTrue(banner.endswith(SmarterFormattedText.RESET))
        lines = banner.split("\n")
        self.assertEqual(lines[1], "=" * 80)
        self.assertEqual(lines[2:5], ["A title", "line one", "line two"])
        self.assertTrue(lines[5].startswith("=" * 80))

    def test_formatted_banner_color(self):
        banner = SmarterFormattedText.banner("A title", color_code=SmarterFormattedText.BRIGHT_GREEN)
        self.assertTrue(banner.startswith(SmarterFormattedText.BRIGHT_GREEN))
        self.assertIn("A title", banner)

    def test_text(self):
        self.assertEqual(SmarterFormattedText.text("x"), f"{SmarterFormattedText.DEFAULT}x{SmarterFormattedText.RESET}")
        self.assertEqual(
            SmarterFormattedText.text("x", SmarterFormattedText.DARK_RED),
            f"{SmarterFormattedText.DARK_RED}x{SmarterFormattedText.RESET}",
        )

    def test_json(self):
        result = SmarterFormattedText.json({"a": 1})
        self.assertTrue(result.startswith(SmarterFormattedText.REGULAR_GREEN))
        self.assertTrue(result.endswith(SmarterFormattedText.RESET))
        self.assertIn('"a"', result)
