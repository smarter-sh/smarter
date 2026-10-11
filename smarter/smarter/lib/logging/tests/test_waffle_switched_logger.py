"""Test smarter.lib.logging.waffle_switched_logger."""

import logging
from unittest.mock import MagicMock

from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestWaffleSwitchedLoggerWrapper(SmarterTestBase):
    """Test that the wrapper gates its logging methods, and delegates everything else to its logger."""

    def wrapper(self, condition: bool) -> tuple[WaffleSwitchedLoggerWrapper, MagicMock]:
        logger = MagicMock(spec=logging.Logger)
        logger.name = "test.logger"
        logger.isEnabledFor.return_value = True
        return WaffleSwitchedLoggerWrapper(logger, lambda level: condition), logger

    def test_exception_always_logs(self):
        """Exception() logs at ERROR, which is above the required level, with the traceback by default."""
        wrapper, logger = self.wrapper(condition=False)
        wrapper.exception("boom %s", 1)
        logger.exception.assert_called_once_with("boom %s", 1, exc_info=True)

    def test_log_follows_the_condition_below_the_required_level(self):
        wrapper, logger = self.wrapper(condition=False)
        wrapper.log(logging.DEBUG, "hidden")
        logger.log.assert_not_called()
        wrapper.log(logging.WARNING, "shown")
        logger.log.assert_called_once_with(logging.WARNING, "shown")
        wrapper, logger = self.wrapper(condition=True)
        wrapper.log(logging.DEBUG, "shown")
        logger.log.assert_called_once_with(logging.DEBUG, "shown")

    def test_getattr_delegates_to_the_logger(self):
        wrapper, logger = self.wrapper(condition=True)
        self.assertTrue(wrapper.isEnabledFor(logging.INFO))
        logger.isEnabledFor.assert_called_once_with(logging.INFO)
        self.assertEqual(wrapper.name, "test.logger")
        with self.assertRaises(AttributeError):
            wrapper.no_such_attribute  # pylint: disable=pointless-statement

    def test_getattr_without_a_logger_does_not_recurse(self):
        """An instance without _logger, e.g. while being copied or unpickled, raises AttributeError."""
        wrapper = WaffleSwitchedLoggerWrapper.__new__(WaffleSwitchedLoggerWrapper)
        with self.assertRaises(AttributeError):
            wrapper.isEnabledFor  # pylint: disable=pointless-statement

    def test_repr(self):
        wrapper, _ = self.wrapper(condition=True)
        self.assertEqual(repr(wrapper), "<WaffleSwitchedLoggerWrapper logger=test.logger>")
