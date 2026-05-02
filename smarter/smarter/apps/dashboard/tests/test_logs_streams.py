"""Tests for dashboard log streaming views."""

from unittest.mock import MagicMock, patch

from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.logs import streams
from smarter.lib.logging.redis_log_handler import build_channel, get_user_context


class TestLogStreams(TestAccountMixin):
    """Regression tests for Redis-backed log streaming."""

    def test_stream_user_logs_subscribes_to_resolved_user_channel(self):
        """The SSE stream should use the same user context as the logging middleware."""
        request = RequestFactory().get("/dashboard/logs/api/stream/")
        request.user = self.non_admin_user

        fake_pubsub = MagicMock()
        fake_cache = MagicMock()
        fake_cache.pubsub.return_value = fake_pubsub

        with (
            patch.object(streams.smarter_settings, "enable_dashboard_server_logs", True),
            patch.object(streams, "get_resolved_user", return_value=self.non_admin_user),
            patch.object(streams, "get_redis_connection", return_value=fake_cache),
        ):
            response = streams.stream_user_logs(request)

        self.assertEqual(response.status_code, 200)
        fake_pubsub.subscribe.assert_called_once_with(build_channel(get_user_context(self.non_admin_user)))
