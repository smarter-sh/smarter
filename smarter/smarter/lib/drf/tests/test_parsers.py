"""Test YAMLParser class."""

from io import BytesIO

from rest_framework.exceptions import ParseError

from smarter.lib.drf.parsers import YAMLParser
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestYAMLParser(SmarterTestBase):
    """Test the YAMLParser class."""

    def setUp(self):
        super().setUp()
        self.parser = YAMLParser()

    def test_parse_valid_yaml(self):
        yaml_data = b"foo: bar\nbaz: 123"
        stream = BytesIO(yaml_data)
        result = self.parser.parse(stream)
        self.assertEqual(result, {"foo": "bar", "baz": 123})

    def test_parse_invalid_yaml(self):
        """Invalid YAML is a ParseError, which DRF answers with a 400, not a 500."""
        yaml_data = b"foo: [unclosed"
        stream = BytesIO(yaml_data)
        with self.assertRaises(ParseError) as ctx:
            self.parser.parse(stream)
        self.assertIn("YAML parse error", str(ctx.exception))

    def test_parse_value_error(self):
        # Simulate a ValueError by patching stream.read to raise ValueError
        class BadStream:
            def read(self):
                raise ValueError("bad stream")

        with self.assertRaises(ParseError) as ctx:
            self.parser.parse(BadStream())
        self.assertIn("YAML parse error", str(ctx.exception))
