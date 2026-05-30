"""Test utility functions."""

from smarter.common.utils import (
    camel_to_snake,
    camel_to_snake_dict,
    pascal_to_snake,
    snake_to_camel,
    to_snake_case,
)
from smarter.lib import logging
from smarter.lib.unittest.base_classes import SmarterTestBase

logger = logging.getLogger(__name__)


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
        logger.debug("test_camel_to_snake_dict - result: %s", result)

        self.assertIn("camel_case", result)
        self.assertIn("nested_dict", result)
        self.assertIn("inner_key", result["nested_dict"])

    def test_snake_to_camel(self):
        self.assertEqual(snake_to_camel("user_name"), "userName")
        self.assertEqual(snake_to_camel(["first_name", "last_name"]), ["firstName", "lastName"])
        self.assertEqual(
            snake_to_camel({"user_name": "alice", "user_profile": {"first_name": "Alice"}}),
            {"userName": "alice", "userProfile": {"firstName": "Alice"}},
        )
        self.assertEqual(snake_to_camel({"user_name": "first_name"}, convert_values=True), {"userName": "firstName"})

    def test_pascal_to_snake(self):
        self.assertEqual(pascal_to_snake("UserProfile"), "user_profile")
        self.assertEqual(pascal_to_snake("FirstName LastName"), "first_name_last_name")

    def test_to_snake_case(self):
        self.assertEqual(to_snake_case("CamelCase"), "camel_case")

        # pylint: disable=C0115
        class DummyClassName:
            pass

        self.assertEqual(to_snake_case(DummyClassName), "dummy_class_name")
