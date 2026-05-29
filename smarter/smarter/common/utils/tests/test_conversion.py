"""Test utility functions."""

from smarter.common.utils import (
    camel_to_snake,
    camel_to_snake_dict,
    dict_is_contained_in,
    dict_is_subset,
    pascal_to_snake,
    recursive_sort_dict,
    rfc1034_compliant_str,
    rfc1034_compliant_to_snake,
    snake_case,
    snake_to_camel,
    to_snake_case,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestConversionUtils(SmarterTestBase):
    """Test conversion utility functions."""

    def test_camel_to_snake(self):
        self.assertEqual(camel_to_snake("camelCase"), "camel_case")
        self.assertEqual(camel_to_snake("CamelCase"), "camel_case")
        self.assertEqual(camel_to_snake("Camel Case"), "camel_case")
        self.assertEqual(camel_to_snake("MyEverlastingSUPERDUPERGobstopper"), "my_everlasting_superduper_gobstopper")
        self.assertEqual(camel_to_snake("already_snake_case"), "already_snake_case")
        self.assertEqual(camel_to_snake(""), "")

    def test_camel_to_snake_dict(self):
        d = {"camelCase": 1, "nestedDict": {"innerKey": 2}}
        result = camel_to_snake_dict(d)
        self.assertIn("camel_case", result)
        self.assertIn("nested_dict", result)
        self.assertIn("inner_key", result["nested_dict"])

    def test_recursive_sort_dict(self):
        d = {"b": 2, "a": {"d": 4, "c": 3}}
        sorted_d = recursive_sort_dict(d)
        self.assertEqual(list(sorted_d.keys()), ["a", "b"])
        self.assertEqual(list(sorted_d["a"].keys()), ["c", "d"])

    def test_dict_is_contained_in_true(self):
        d1 = {"a": 1, "b": {"c": 2}}
        d2 = {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}
        self.assertTrue(dict_is_contained_in(d1, d2))

    def test_dict_is_contained_in_false(self):
        d1 = {"a": 1, "b": {"c": 999}}
        d2 = {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}
        self.assertFalse(dict_is_contained_in(d1, d2))

    def test_dict_is_subset_true(self):
        big = {
            "name": "Alice",
            "profile": {"age": 30, "city": "Wonderland"},
            "roles": ["admin", "user"],
        }
        small = {"profile": {"age": 30}, "roles": ["admin"]}
        self.assertTrue(dict_is_subset(small, big))

    def test_dict_is_subset_false(self):
        big = {"profile": {"age": 30, "city": "Wonderland"}, "roles": ["admin", "user"]}
        small = {"profile": {"age": 31}}
        self.assertFalse(dict_is_subset(small, big))

    def test_snake_to_camel(self):
        self.assertEqual(snake_to_camel("user_name"), "userName")
        self.assertEqual(snake_to_camel(["first_name", "last_name"]), ["firstName", "lastName"])
        self.assertEqual(
            snake_to_camel({"user_name": "alice", "user_profile": {"first_name": "Alice"}}),
            {"userName": "alice", "userProfile": {"firstName": "Alice"}},
        )
        self.assertEqual(snake_to_camel({"user_name": "first_name"}, convert_values=True), {"userName": "firstName"})

    def test_snake_case(self):
        self.assertEqual(snake_case("UserProfile"), "userprofile")
        self.assertEqual(snake_case("FirstName LastName"), "firstname_lastname")
        self.assertEqual(snake_case("already_snake_case"), "already_snake_case")

    def test_pascal_to_snake(self):
        self.assertEqual(pascal_to_snake("UserProfile"), "user_profile")
        self.assertEqual(pascal_to_snake("FirstName LastName"), "first_name_last_name")

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

    def test_to_snake_case(self):
        self.assertEqual(to_snake_case("CamelCase"), "camel_case")

        # pylint: disable=C0115
        class Dummy:
            __name__ = "CamelCase"

        self.assertEqual(to_snake_case(Dummy), "camel_case")
