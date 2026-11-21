"""Test :mod:`smarter.apps.vectorsearch.receivers`, the signal receivers of the vectorsearch app."""

import logging
from unittest.mock import MagicMock

from smarter.apps.vectorsearch import receivers
from smarter.apps.vectorsearch.signals import vectorsearch_called
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.log_capture import WrappedLoggerCapture


class TestVectorsearchReceivers(SmarterTestBase):
    """Test the receiver that logs a Vectorsearch's call."""

    def test_called(self):
        capture = WrappedLoggerCapture(self, receivers.logger)
        vectorsearch_called.send(sender=self.__class__, vectorsearch=MagicMock(pk=42), request=None, args=(), kwargs={})
        self.assertIn("running vectorsearch 42", capture.text(logging.INFO))
