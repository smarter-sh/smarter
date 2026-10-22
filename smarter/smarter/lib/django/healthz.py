"""
An ASGI application that answers the liveness probe, ``/healthz/``, before Django does.

Kubernetes restarts a pod whose liveness probe fails. When ``/healthz/`` was a Django view, its
answer depended on the whole middleware stack, which reads the session from Redis and the user
from the database. A pod under load, or one whose Redis or database stalled, then failed its
liveness probe and was restarted, which moved its load onto the other pods. Liveness should only
say whether the server process is alive and its event loop is running, which this application
answers without a thread, a query or a cache lookup. Whether the pod can serve requests is the
readiness probe's question, ``/readiness/``, which still goes through Django, so a pod that can't
is taken out of the service rather than restarted.

See ``helm/charts/smarter/templates/deployment-app.yaml``.
"""

from asgiref.typing import (
    ASGI3Application,
    ASGIReceiveCallable,
    ASGISendCallable,
    Scope,
)

HEALTHZ_PATHS = frozenset({"/healthz", "/healthz/"})
"""The liveness probe's paths."""


class HealthzASGIMiddleware:
    """
    Answer ``GET`` and ``HEAD`` requests for ``/healthz/`` with ``200 OK``, and pass every other request to the app.

    :param app: The ASGI application to wrap, e.g. Django's.

    Example:

    .. code-block:: python

        application = HealthzASGIMiddleware(get_asgi_application())
    """

    def __init__(self, app: ASGI3Application):
        self.app = app

    async def __call__(self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable) -> None:
        """
        Handle one ASGI connection.

        :param scope: The connection's scope.
        :param receive: The callable that receives the connection's events.
        :param send: The callable that sends events to the client.
        """
        if scope["type"] == "http" and scope["path"] in HEALTHZ_PATHS and scope["method"] in ("GET", "HEAD"):
            # a HEAD response has the GET response's headers, without its body.
            body = b"OK" if scope["method"] == "GET" else b""
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"text/plain"), (b"content-length", b"2")],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)
