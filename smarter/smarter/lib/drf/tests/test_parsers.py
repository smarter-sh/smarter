"""test YAMLParser class"""

from io import BytesIO

from rest_framework.exceptions import ParseError

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..parsers import YAMLParser


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
        # This will raise a yaml.YAMLError, not ValueError, so it will propagate
        yaml_data = b"foo: [unclosed"
        stream = BytesIO(yaml_data)
        with self.assertRaises(Exception):
            self.parser.parse(stream)

    def test_parse_value_error(self):
        # Simulate a ValueError by patching stream.read to raise ValueError
        class BadStream:
            def read(self):
                raise ValueError("bad stream")

        with self.assertRaises(ParseError) as ctx:
            self.parser.parse(BadStream())
        self.assertIn("YAML parse error", str(ctx.exception))
