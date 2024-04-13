"""Django Rest Framework YAML parser."""

import yaml
from rest_framework.exceptions import ParseError
from rest_framework.parsers import BaseParser


class YAMLParser(BaseParser):
    """A custom parser for YAML request payloads."""

    media_type = "application/x-yaml"

    def parse(self, stream, media_type=None, parser_context=None):
        # pylint: disable=W0707
        try:
            data = stream.read().decode("utf-8")
            return yaml.safe_load(data)
        except ValueError as exc:
            raise ParseError(f"YAML parse error - {str(exc)}")
