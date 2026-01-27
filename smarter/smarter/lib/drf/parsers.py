"""Django Rest Framework YAML parser."""

import logging

import yaml
from rest_framework.exceptions import ParseError
from rest_framework.parsers import BaseParser

from smarter.common.helpers.console_helpers import formatted_text

logger = logging.getLogger(__name__)
logger_prefix = formatted_text(f"{__name__}.YAMLParser()")


class YAMLParser(BaseParser):
    """A custom parser for YAML request payloads."""

    media_type = "application/x-yaml"

    def parse(self, stream, media_type=None, parser_context=None):
        # pylint: disable=W0707
        try:
            data = stream.read().decode("utf-8")
            retval = yaml.safe_load(data)
            logger.debug("%s.parse() - successfully parsed YAML data: %s", logger_prefix, retval)
            return retval
        except ValueError as exc:
            raise ParseError(f"{logger_prefix}.parse() YAML parse error - {str(exc)}")
