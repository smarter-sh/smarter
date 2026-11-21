"""Test :mod:`smarter.apps.llmhost.receivers`, the signal receivers of the llmhost app."""

import logging
from unittest.mock import MagicMock

from smarter.apps.llmhost import receivers
from smarter.apps.llmhost.signals import (
    llmhost_destroyed,
    llmhost_launch_failed,
    llmhost_launched,
)
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.log_capture import WrappedLoggerCapture


class TestLLMHostReceivers(SmarterTestBase):
    """Test the receivers that log an LLMHost's launch, failed launch and destruction."""

    def setUp(self):
        super().setUp()
        self.capture = WrappedLoggerCapture(self, receivers.logger)
        self.llmhost = MagicMock(__str__=lambda self: "qwen-host")

    def test_launched(self):
        llmhost_launched.send(sender=self.__class__, llmhost=self.llmhost, resources={"nodes": 1})
        self.assertIn("launched qwen-host: {'nodes': 1}", self.capture.text(logging.INFO))

    def test_destroyed(self):
        llmhost_destroyed.send(sender=self.__class__, llmhost=self.llmhost, purge=True)
        self.assertIn("destroyed qwen-host, purge=True", self.capture.text(logging.INFO))

    def test_launch_failed(self):
        llmhost_launch_failed.send(sender=self.__class__, llmhost=self.llmhost, error="the cluster is unavailable")
        self.assertIn("could not launch qwen-host: the cluster is unavailable", self.capture.text(logging.WARNING))
