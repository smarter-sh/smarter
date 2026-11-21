"""Test :mod:`smarter.lib.unittest.log_capture`."""

import logging

from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.log_capture import WrappedLoggerCapture


def log_two_messages(logger: WaffleSwitchedLoggerWrapper):
    """Log one message at DEBUG and one at WARNING."""
    logger.debug("debug %s", 1)
    logger.warning("warning %s", 2)


class TestWrappedLoggerCapture(SmarterTestBase):
    """Test WrappedLoggerCapture."""

    def setUp(self):
        super().setUp()
        # a condition that is always off: the capture must ignore it.
        self.logger = WaffleSwitchedLoggerWrapper(logging.getLogger("smarter.test.log_capture"), lambda level: False)
        self.capture = WrappedLoggerCapture(self, self.logger)

    def test_captures_every_level_with_the_prefix(self):
        log_two_messages(self.logger)
        self.assertEqual(self.capture.count(), 2)
        debug_message = self.capture.messages(logging.DEBUG)[0]
        self.assertIn("log_two_messages()", debug_message)
        self.assertTrue(debug_message.endswith(" debug 1"))
        self.assertIn("warning 2", self.capture.text(logging.WARNING))
        self.assertEqual(self.capture.count(logging.INFO), 0)

    def test_clear(self):
        log_two_messages(self.logger)
        self.capture.clear()
        self.assertEqual(self.capture.text(), "")
