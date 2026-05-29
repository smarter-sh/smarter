"""Test utility functions."""

from smarter.common.utils import (
    rfc1034_compliant_str,
    rfc1034_compliant_to_snake,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestConversionUtils(SmarterTestBase):
    """Test conversion utility functions."""

    def test_rfc1034_compliant_str(self):
        self.assertEqual(rfc1034_compliant_str("My_ChatBot_2025"), "my-chatbot-2025")
        self.assertEqual(rfc1034_compliant_str("My@Bot!_Name"), "my-bot-name")
        long_name = "ThisIsAReallyLongChatBotNameThatShouldBeTruncatedToSixtyThreeCharacters_Extra"
        self.assertEqual(
            rfc1034_compliant_str(long_name), "thisisareallylongchatbotnamethatshouldbetruncatedtosixtythreecharacters"
        )

    def test_rfc1034_compliant_str_invalid(self):
        with self.assertRaises(Exception):
            rfc1034_compliant_str(12345)
        with self.assertRaises(Exception):
            rfc1034_compliant_str("")

    def test_rfc1034_compliant_to_snake(self):
        self.assertEqual(rfc1034_compliant_to_snake("my-chatbot-2025"), "my_chatbot_2025")
        self.assertEqual(rfc1034_compliant_to_snake("simplelabel"), "simplelabel")
        self.assertEqual(rfc1034_compliant_to_snake("this-is-a-test-label"), "this_is_a_test_label")
        with self.assertRaises(Exception):
            rfc1034_compliant_to_snake(12345)
