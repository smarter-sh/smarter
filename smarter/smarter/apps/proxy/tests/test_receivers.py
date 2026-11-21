"""Test :mod:`smarter.apps.proxy.receivers`, which log each proxied request once."""

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

from smarter.apps.proxy import receivers
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.log_capture import WrappedLoggerCapture


class TestProxyReceivers(SmarterTestBase):
    """Test the proxy request receivers."""

    def setUp(self):
        super().setUp()
        self.capture = WrappedLoggerCapture(self, receivers.logger)
        self.proxy = MagicMock()
        self.proxy.name = "weather"

    def test_completed_is_logged_at_info(self):
        receivers.log_proxy_request_completed(
            sender=None,
            proxy=self.proxy,
            user_profile="pk=1",
            method="GET",
            path="/forecast",
            status=200,
            usage={"tokens": 3},
            elapsed=0.25,
        )
        self.assertIn("Proxy weather: GET /forecast -> 200 in 0.25s", self.capture.text(logging.INFO))

    def test_refused_is_logged_at_warning_with_its_code(self):
        error = SimpleNamespace(code="budget_exceeded")
        receivers.log_proxy_request_failed(
            sender=None, proxy=self.proxy, user_profile="pk=1", method="POST", path="/x", error=error, elapsed=0.1
        )
        warning = self.capture.text(logging.WARNING)
        self.assertIn("Proxy weather: POST /x refused for pk=1: budget_exceeded", warning)
