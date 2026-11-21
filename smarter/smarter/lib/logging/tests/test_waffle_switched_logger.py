"""Test smarter.lib.logging.waffle_switched_logger."""

import logging
from unittest.mock import MagicMock

from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.lib.logging import WaffleSwitchedLoggerWrapper, getSmarterLogger
from smarter.lib.unittest.base_classes import SmarterTestBase

LOGGER_NAME = "smarter.test.waffle_switched_logger"
"""A logger of the test's own, so that assertLogs sees only what these tests log."""


def prefix_of(name: str) -> str:
    """Return the formatted prefix that the wrapper writes for a caller named ``name``."""
    return SmarterFormattedText.text(f"{__name__}.{name}()")


class Base:
    """A class whose method a subclass inherits."""

    def __init__(self, logger: WaffleSwitchedLoggerWrapper):
        self.logger = logger

    def log_something(self):
        """Log one message."""
        self.logger.info("something happened")

    @classmethod
    def log_from_classmethod(cls, logger: WaffleSwitchedLoggerWrapper):
        """Log one message from a classmethod."""
        logger.info("something happened")


class Subclass(Base):
    """A subclass that inherits Base's methods."""


def log_from_function(logger: WaffleSwitchedLoggerWrapper):
    """Log one message from a module-level function."""
    logger.info("something happened")


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
        logger.log.assert_called_once()
        level, message, argument = logger.log.call_args.args
        self.assertEqual(level, logging.ERROR)
        self.assertEqual(message, prefix_of("TestWaffleSwitchedLoggerWrapper.test_exception_always_logs") + " boom %s")
        self.assertEqual(argument, 1)
        self.assertTrue(logger.log.call_args.kwargs["exc_info"])

    def test_log_follows_the_condition_below_the_required_level(self):
        wrapper, logger = self.wrapper(condition=False)
        wrapper.log(logging.DEBUG, "hidden")
        wrapper.debug("hidden")
        wrapper.info("hidden")
        logger.log.assert_not_called()
        wrapper.log(logging.WARNING, "shown")
        logger.log.assert_called_once()
        wrapper, logger = self.wrapper(condition=True)
        wrapper.log(logging.DEBUG, "shown")
        logger.log.assert_called_once()

    def test_a_disabled_level_is_not_logged(self):
        """Above the required level too, a level that the logger isn't enabled for logs nothing."""
        wrapper, logger = self.wrapper(condition=True)
        logger.isEnabledFor.return_value = False
        wrapper.error("hidden")
        logger.log.assert_not_called()

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


class TestCallerPrefix(SmarterTestBase):
    """Test that every message starts with the name of the function or method that logged it."""

    def setUp(self):
        super().setUp()
        self.logger = getSmarterLogger(LOGGER_NAME)

    def logged(self, call) -> logging.LogRecord:
        """Run ``call`` and return the one record it logged."""
        with self.assertLogs(LOGGER_NAME, level=logging.DEBUG) as captured:
            call()
        self.assertEqual(len(captured.records), 1)
        return captured.records[0]

    def test_function(self):
        record = self.logged(lambda: log_from_function(self.logger))
        self.assertEqual(record.getMessage(), prefix_of("log_from_function") + " something happened")

    def test_method_of_the_class_that_defines_it(self):
        record = self.logged(lambda: Base(self.logger).log_something())
        self.assertEqual(record.getMessage(), prefix_of("Base.log_something") + " something happened")

    def test_inherited_method_is_named_after_the_subclass(self):
        record = self.logged(lambda: Subclass(self.logger).log_something())
        self.assertEqual(record.getMessage(), prefix_of("Subclass.log_something") + " something happened")

    def test_classmethod_is_named_after_the_class_it_was_called_on(self):
        record = self.logged(lambda: Subclass.log_from_classmethod(self.logger))
        self.assertEqual(record.getMessage(), prefix_of("Subclass.log_from_classmethod") + " something happened")

    def test_the_record_points_at_the_caller(self):
        """The record's funcName and lineno are the caller's, not the wrapper's."""
        record = self.logged(lambda: log_from_function(self.logger))
        self.assertEqual(record.funcName, "log_from_function")
        self.assertTrue(record.pathname.endswith("test_waffle_switched_logger.py"))

    def test_arguments_are_formatted(self):
        record = self.logged(lambda: self.logger.warning("%s of %d", "one", 2))
        self.assertTrue(record.getMessage().endswith(" one of 2"))

    def test_a_percent_sign_without_arguments_is_kept(self):
        """A message without arguments isn't %-formatted, so its % signs come through as they are."""
        record = self.logged(lambda: self.logger.info("100% done"))
        self.assertTrue(record.getMessage().endswith(" 100% done"))

    def test_a_mapping_argument_still_works(self):
        record = self.logged(lambda: self.logger.info("%(count)d items", {"count": 3}))
        self.assertTrue(record.getMessage().endswith(" 3 items"))

    def test_prefix_format(self):
        """A prefix_format colors the caller's name, and isn't passed on to the wrapped logger."""
        blue = SmarterFormattedText.BOLD_DARK_BLUE
        for method in ("debug", "info", "warning", "error", "critical", "exception"):
            with self.subTest(method=method):
                log = getattr(self.logger, method)
                record = self.logged(
                    lambda: log("cache cleared", prefix_format=blue)
                )  # pylint: disable=cell-var-from-loop
                self.assertTrue(record.getMessage().startswith(blue + f"{__name__}."))
                self.assertTrue(record.getMessage().endswith(" cache cleared"))
        record = self.logged(lambda: self.logger.log(logging.INFO, "cache cleared", prefix_format=blue))
        self.assertTrue(record.getMessage().startswith(blue))

    def test_the_default_prefix_format(self):
        record = self.logged(lambda: log_from_function(self.logger))
        self.assertTrue(record.getMessage().startswith(SmarterFormattedText.DEFAULT))

    def test_a_message_that_is_not_a_string(self):
        record = self.logged(lambda: self.logger.error(ValueError("bad value")))
        self.assertTrue(record.getMessage().endswith(" bad value"))
