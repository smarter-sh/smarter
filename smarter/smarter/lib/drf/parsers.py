"""Django Rest Framework YAML parser."""

import yaml
from rest_framework.exceptions import ParseError
from rest_framework.parsers import BaseParser

from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = f"{SmarterFormattedText.text(__name__)}.YAMLParser()"

YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
"""PyYAML's C safe loader when PyYAML was built with libyaml, which is much faster, else the pure Python one."""


class YAMLParser(BaseParser):
    """A custom parser for YAML request payloads."""

    media_type = "application/x-yaml"

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parse a UTF-8 YAML request body.

        The body itself is never logged: a manifest, such as a Secret's, can hold credentials.

        :param stream: The request body stream.
        :param media_type: The request's media type, unused.
        :param parser_context: DRF's parser context, unused.
        :returns: The parsed data.
        :raises ParseError: If the body is not UTF-8, or not valid YAML.
        """
        try:
            data = stream.read().decode("utf-8")
            retval = yaml.load(data, Loader=YAML_LOADER)  # nosec B506 - a safe loader
        except (ValueError, yaml.YAMLError) as exc:
            # the parser's own message stays in the log: it describes the parser's internals, and
            # quotes the body, which the client already has.
            logger.debug("%s.parse() YAML parse error: %s", logger_prefix, exc)
            raise ParseError("YAML parse error - the request body is not valid UTF-8 YAML.") from exc
        logger.debug("%s.parse() parsed a YAML body of type %s", logger_prefix, type(retval).__name__)
        return retval
