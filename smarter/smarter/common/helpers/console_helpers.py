"""
Console helpers for formatting output.

:class:`SmarterFormattedText` colors text, JSON and banners with ANSI codes for the logs, e.g.
``logger_prefix = logging.SmarterFormattedText.text(__name__)``.

This module doesn't import Django, so that modules that load before Django is set up, such
as :mod:`smarter.common.conf.settings`, can use it. :mod:`smarter.lib.logging` re-exports it.
"""

from typing import Union

from smarter.lib import json
from smarter.lib.json import SmarterJSONEncoder
from smarter.lib.typing import SmarterDictType


class SmarterFormattedText:
    """
    ANSI color codes, and methods that color text, JSON and banners for the logs.

    Example::

        SmarterFormattedText.text("NOT_READY", SmarterFormattedText.DARK_RED)
    """

    BRIGHT_GREEN = "\033[92m"
    REGULAR_GREEN = "\033[32m"
    DARK_RED = "\033[31m"
    BOLD_DARK_BLUE = "\033[1;34m"
    LIGHT_GRAY = "\033[37m"
    DEFAULT = "\033[1;31m"
    """Bold dark red, the color of every log message's origin prefix."""
    RESET = "\033[0m"

    @classmethod
    def text(cls, text: str, color_code: str = DEFAULT) -> str:
        """
        Color a string.

        :param text: The text to color.
        :param color_code: The ANSI color code to apply, e.g. :attr:`DARK_RED`.
        :returns: The text between the color code and :attr:`RESET`.
        """
        return f"{color_code}{text}{cls.RESET}"

    @classmethod
    def json(cls, json_obj: Union[SmarterDictType, list]) -> str:
        """
        Serialize a JSON object, colored green.

        :param json_obj: The dict or list to serialize.
        :returns: The JSON, between :attr:`REGULAR_GREEN` and :attr:`RESET`.
        """
        return cls.text(json.dumps(json_obj, cls=SmarterJSONEncoder), cls.REGULAR_GREEN)

    @classmethod
    def banner(cls, title: str, *lines: str, color_code: str = DEFAULT) -> str:
        """
        Format an attention-grabbing, multi-line console banner, e.g. for a missing configuration.

        Example::

            logger.error(SmarterFormattedText.banner("SMTP is not configured.", "Set SMARTER_SMTP_USERNAME in .env."))

        :param title: The first line of the banner.
        :param lines: Further lines, e.g. instructions.
        :param color_code: The ANSI color code to apply.
        :returns: The banner, framed by rules and preceded by a newline, with ANSI color codes.
        """
        rule = "=" * 80
        body = "\n".join([title, *lines])
        return cls.text(f"\n{rule}\n{body}\n{rule}", color_code)
