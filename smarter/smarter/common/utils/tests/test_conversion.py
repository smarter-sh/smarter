"""Test utility functions."""

from smarter.common.utils import (
    to_camel_case,
    to_snake_case,
)
from smarter.lib import logging
from smarter.lib.unittest.base_classes import SmarterTestBase

logger = logging.getLogger(__name__)


class TestConversionUtils(SmarterTestBase):
    """Test conversion utility functions."""

    def test_camel_to_snake(self):
        self.assertEqual(to_snake_case("camelCase"), "camel_case")
        self.assertEqual(to_snake_case("CamelCase"), "camel_case")
        self.assertEqual(to_snake_case("Camel Case"), "camel_case")
        self.assertEqual(to_snake_case("MyEverlastingSUPERDUPERGobstopper"), "my_everlasting_superduper_gobstopper")
        self.assertEqual(to_snake_case("already_snake_case"), "already_snake_case")
        self.assertEqual(to_snake_case(""), "")

    def test_camel_to_snake_dict(self):
        d = {"camelCase": 1, "nestedDict": {"innerKey": 2}}
        result = to_snake_case(d)
        logger.debug("test_camel_to_snake_dict - result: %s", result)

        self.assertIn("camel_case", result)
        self.assertIn("nested_dict", result)
        self.assertIn("inner_key", result["nested_dict"])

    def test_snake_to_camel(self):
        self.assertEqual(to_camel_case("user_name"), "userName")
        self.assertEqual(to_camel_case(["first_name", "last_name"]), ["firstName", "lastName"])
        self.assertEqual(
            to_camel_case({"user_name": "alice", "user_profile": {"first_name": "Alice"}}),
            {"userName": "alice", "userProfile": {"firstName": "Alice"}},
        )
        self.assertEqual(to_camel_case({"user_name": "first_name"}, convert_values=True), {"userName": "firstName"})

    def test_pascal_to_snake(self):
        self.assertEqual(to_snake_case("UserProfile"), "user_profile")
        self.assertEqual(to_snake_case("FirstName LastName"), "first_name_last_name")

    def test_to_snake_case(self):
        self.assertEqual(to_snake_case("CamelCase"), "camel_case")

        # pylint: disable=C0115
        class DummyClassName:
            pass

        self.assertEqual(to_snake_case(DummyClassName), "dummy_class_name")
