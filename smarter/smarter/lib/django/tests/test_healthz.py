"""Test HealthzASGIMiddleware."""

import asyncio
from unittest.mock import AsyncMock

from smarter.lib.django.healthz import HealthzASGIMiddleware
from smarter.lib.unittest.base_classes import SmarterTestBase


def http_scope(path: str, method: str = "GET") -> dict:
    """A minimal ASGI http scope."""
    return {"type": "http", "path": path, "method": method, "headers": []}


class TestHealthzASGIMiddleware(SmarterTestBase):
    """Test that the liveness probe is answered without the wrapped app, and every other request is passed to it."""

    def call(self, scope: dict) -> tuple[AsyncMock, list]:
        """Call the middleware with the scope, and return the wrapped app and the messages sent."""
        app = AsyncMock()
        sent: list = []

        async def send(message):
            sent.append(message)

        asyncio.run(HealthzASGIMiddleware(app)(scope, AsyncMock(), send))
        return app, sent

    def test_healthz(self):
        """Test that GET /healthz/ is 200 OK, and never reaches the app."""
        for path in ("/healthz/", "/healthz"):
            with self.subTest(path=path):
                app, sent = self.call(http_scope(path))
                app.assert_not_called()
                self.assertEqual(sent[0]["status"], 200)
                self.assertIn((b"content-type", b"text/plain"), sent[0]["headers"])
                self.assertEqual(sent[1], {"type": "http.response.body", "body": b"OK"})

    def test_head(self):
        """Test that HEAD /healthz/ is 200, without a body."""
        app, sent = self.call(http_scope("/healthz/", "HEAD"))
        app.assert_not_called()
        self.assertEqual(sent[0]["status"], 200)
        self.assertEqual(sent[1]["body"], b"")

    def test_other_requests(self):
        """Test that other paths, other methods, websockets and lifespan events reach the app."""
        scopes = [
            http_scope("/readiness/"),
            http_scope("/healthz/extra/"),
            http_scope("/healthz/", "POST"),
            {"type": "websocket", "path": "/healthz/"},
            {"type": "lifespan"},
        ]
        for scope in scopes:
            with self.subTest(scope=scope):
                app, sent = self.call(scope)
                app.assert_awaited_once()
                self.assertEqual(sent, [])
