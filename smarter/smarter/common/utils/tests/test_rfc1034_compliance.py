"""Test utility functions."""

from smarter.common.utils import (
    rfc1034_compliant_str,
    rfc1034_compliant_to_snake,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestConversionUtils(SmarterTestBase):
    """Test conversion utility functions."""

    def test_rfc1034_compliant_str(self):
        self.assertEqual(rfc1034_compliant_str("My_LLMClient_2025"), "my-llmclient-2025")
        self.assertEqual(rfc1034_compliant_str("My@Bot!_Name"), "mybot-name")
        long_name = "ThisIsAReallyLongLLMClientNameThatShouldBeTruncatedToSixtyThreeCharacters_Extra"
        self.assertEqual(
            rfc1034_compliant_str(long_name),
            "thisisareallylongllmclientnamethatshouldbetruncatedtosixtythreecharacters"[:63],
        )

    def test_rfc1034_compliant_str_invalid(self):
        with self.assertRaises(Exception):
            rfc1034_compliant_str(12345)
        with self.assertRaises(Exception):
            rfc1034_compliant_str("")

    def test_rfc1034_compliant_to_snake(self):
        self.assertEqual(rfc1034_compliant_to_snake("my-llm_client-2025"), "my_llm_client_2025")
        self.assertEqual(rfc1034_compliant_to_snake("simplelabel"), "simplelabel")
        self.assertEqual(rfc1034_compliant_to_snake("this-is-a-test-label"), "this_is_a_test_label")
        with self.assertRaises(Exception):
            rfc1034_compliant_to_snake(12345)
