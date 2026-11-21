"""
Capture what modules log through their wrapped loggers, prefix included.

A module's ``logger`` is a :class:`~smarter.lib.logging.waffle_switched_logger.WaffleSwitchedLoggerWrapper`,
which starts each message with the dotted name of the function that logged it. A test that replaces
the whole ``logger`` with a mock skips the wrapper, so it never sees that name.
:class:`WrappedLoggerCapture` replaces only the logger that the wrapper wraps, and the wrapper's
condition, so that every message is captured at every level, exactly as it would be emitted::

    capture = WrappedLoggerCapture(self, receivers.logger)
    plugin_created.send(sender=self.__class__, plugin=plugin)
    self.assertIn("plugin_created()", capture.text())
"""

import logging
import unittest
from unittest import mock

from smarter.lib.logging import WaffleSwitchedLoggerWrapper


class WrappedLoggerCapture:
    """
    Capture the formatted messages of one or more wrapped loggers until the test ends.

    :param test_case: The running test. The patches are undone by its cleanup.
    :param loggers: The modules' loggers, e.g. ``receivers.logger``.
    """

    def __init__(self, test_case: unittest.TestCase, *loggers: WaffleSwitchedLoggerWrapper):
        self.records: list[tuple[int, str]] = []
        self.mock = mock.MagicMock(spec=logging.Logger)
        self.mock.isEnabledFor.return_value = True
        self.mock.log.side_effect = self._record
        for logger in loggers:
            for attribute, value in (("_logger", self.mock), ("_condition_func", None)):
                patcher = mock.patch.object(logger, attribute, value)
                patcher.start()
                test_case.addCleanup(patcher.stop)

    def _record(self, level: int, msg, *args, **kwargs):  # pylint: disable=unused-argument
        """Record one message, formatted while the objects it describes still exist."""
        message = msg % args if args else msg
        self.records.append((level, message))

    def messages(self, level: "int | None" = None) -> list[str]:
        """
        Return the captured messages, in the order they were logged.

        :param level: Only the messages logged at this level, e.g. ``logging.INFO``, or all of them.
        :returns: The formatted messages, each starting with its caller's prefix.
        """
        selected = []
        for record_level, message in self.records:
            if level is None or record_level == level:
                selected.append(message)
        return selected

    def text(self, level: "int | None" = None) -> str:
        """
        Return the captured messages as one string.

        :param level: Only the messages logged at this level, or all of them.
        :returns: The messages, one per line.
        """
        return "\n".join(self.messages(level))

    def count(self, level: "int | None" = None) -> int:
        """
        Return how many messages were captured.

        :param level: Only count the messages logged at this level, or all of them.
        :returns: The number of messages.
        """
        return len(self.messages(level))

    def clear(self) -> None:
        """Forget the messages captured so far."""
        self.records.clear()
