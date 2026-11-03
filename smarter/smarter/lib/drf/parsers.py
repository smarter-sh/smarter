"""Django Rest Framework YAML parser."""

import yaml
from rest_framework.exceptions import ParseError
from rest_framework.parsers import BaseParser

from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = f"{SmarterFormattedText.text(__name__)}.YAMLParser()"


class YAMLParser(BaseParser):
    """A custom parser for YAML request payloads."""

    media_type = "application/x-yaml"

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parse a UTF-8 YAML request body.

        :param stream: The request body stream.
        :param media_type: The request's media type, unused.
        :param parser_context: DRF's parser context, unused.
        :returns: The parsed data.
        :raises ParseError: If the body is not valid YAML.
        """
        # pylint: disable=W0707
        try:
            data = stream.read().decode("utf-8")
            retval = yaml.safe_load(data)
            logger.debug("%s.parse() - successfully parsed YAML data: %s", logger_prefix, retval)
            return retval
        except ValueError as exc:
            raise ParseError(f"{logger_prefix}.parse() YAML parse error - {str(exc)}")
