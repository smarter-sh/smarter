"""Tests for smarter.workers.liveness, the Celery workers' liveness probe.

The broker is never contacted: the Celery app is replaced.
"""

import os
from unittest import mock

from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.workers import liveness

CELERY = "smarter.workers.liveness.Celery"
NODE = "celery@smarter-worker-5b7f794fb-dw7mx"


class TestLiveness(SmarterTestBase):
    """Test ping_worker() and main()."""

    def fake_app(self, replies) -> mock.MagicMock:
        app = mock.MagicMock()
        app.control.ping.return_value = replies
        return app

    def test_broker_url(self):
        with mock.patch.dict(os.environ, {"CELERY_BROKER_URL": "redis://broker:6379/0"}):
            self.assertEqual(liveness.broker_url(), "redis://broker:6379/0")
        with mock.patch.dict(os.environ, {"CELERY_BROKER_URL": ""}):
            self.assertEqual(liveness.broker_url(), liveness.DEFAULT_BROKER_URL)

    def test_ping_worker_answered(self):
        app = self.fake_app([{NODE: {"ok": "pong"}}])
        with mock.patch(CELERY, return_value=app) as celery:
            self.assertTrue(liveness.ping_worker(NODE, "redis://broker:6379/0", timeout=3))
        celery.assert_called_once_with("smarter-liveness", broker="redis://broker:6379/0")
        app.control.ping.assert_called_once_with(destination=[NODE], timeout=3)
        app.close.assert_called_once()

    def test_ping_worker_silent(self):
        """No answer, or only another worker's, is not alive."""
        for replies in (None, [], [{"celery@another-pod": {"ok": "pong"}}]):
            with self.subTest(replies=replies), mock.patch(CELERY, return_value=self.fake_app(replies)):
                self.assertFalse(liveness.ping_worker(NODE, "redis://broker:6379/0"))

    def test_main(self):
        with mock.patch.object(liveness, "ping_worker", return_value=True) as ping:
            self.assertEqual(liveness.main([NODE]), 0)
        self.assertEqual(ping.call_args.args[0], NODE)
        with mock.patch.object(liveness, "ping_worker", return_value=False):
            self.assertEqual(liveness.main([NODE]), 1)
        with mock.patch.object(liveness, "ping_worker", side_effect=ConnectionError("Redis is down")):
            self.assertEqual(liveness.main([NODE]), 1)

    def test_main_defaults_to_the_pod(self):
        """Without an argument, the node name is celery@ and the pod's HOSTNAME."""
        with (
            mock.patch.dict(os.environ, {"HOSTNAME": "smarter-worker-abc"}),
            mock.patch.object(liveness, "ping_worker", return_value=True) as ping,
        ):
            self.assertEqual(liveness.main([]), 0)
        self.assertEqual(ping.call_args.args[0], "celery@smarter-worker-abc")
