"""Test serializers for converting objects to JSON."""

import datetime

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..serializers import dumps, serialize_python_dict


class TestSerializers(SmarterTestBase):
    """Test serializers for converting objects to JSON."""

    def test_dumps_with_datetime(self):
        data = {"now": datetime.datetime(2024, 1, 1, 12, 0, 0)}
        json_str = dumps(data)
        self.assertIn("2024-01-01T12:00:00", json_str)

    def test_dumps_with_unknown_type(self):
        class Foo:
            pass

        data = {"foo": Foo()}
        with self.assertRaises(TypeError):
            dumps(data)

    def test_serialize_python_dict(self):
        data = {"a": 1, "b": 2}
        result = serialize_python_dict(data)
        self.assertEqual(result, data)

    def test_serialize_python_dict_with_datetime(self):
        data = {"now": datetime.datetime(2024, 1, 1, 12, 0, 0)}
        result = serialize_python_dict(data)
        self.assertEqual(result["now"], "2024-01-01T12:00:00")
