"""
SSE log streaming views for dashboard clients.

This module provides a login-protected Django view,
:func:`stream_user_logs`, that streams server log output to the browser using
Server-Sent Events (SSE).

The view subscribes to a Redis Pub/Sub channel derived from the authenticated
user context and forwards log records to connected clients in SSE format.

Behavior
--------

- Uses the ``default`` Redis connection configured through ``django-redis``.
- Verifies ``smarter_settings.enable_dashboard_server_logs`` before opening a
    stream.
- Emits a retry hint and keepalive comments to keep long-lived connections
    healthy through intermediate proxies.
- Closes the Redis Pub/Sub connection when the stream terminates.

SSE payload format
------------------

- ``retry: 3000`` is sent once when a client first connects.
- Each log line is sent as ``data: <line>`` followed by a blank line.
- ``: keepalive`` comments are sent during idle periods.

See Also
--------

- :mod:`smarter.lib.logging.redis_log_handler`
"""

import asyncio
from http import HTTPStatus
from typing import Union

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django_redis import get_redis_connection
from redis.exceptions import RedisError

from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.logging.redis_log_handler import (
    build_channel,
    get_user_context,
    job_id_factory,
)

logger = logging.getLogger(__name__)


# pylint: disable=W0613
@login_required
def stream_user_logs(request: HttpRequest) -> Union[StreamingHttpResponse, HttpResponse]:
    """
    Stream per-user server logs over Server-Sent Events (SSE).

    This endpoint opens a Redis Pub/Sub subscription for the current user
    context and forwards incoming messages as SSE frames. When no message is
    available, keepalive comments are emitted so that long-lived connections
    remain active through reverse proxies.

    :param request: Incoming HTTP request. The view requires authentication
        via :func:`django.contrib.auth.decorators.login_required`.
    :type request: django.http.HttpRequest
    :returns:
        A streaming SSE response when log streaming is available; otherwise a
        plain-text non-streaming response describing why streaming is disabled
        or unavailable.
    :rtype: Union[django.http.StreamingHttpResponse, django.http.HttpResponse]

    :status 200: Streaming response created successfully.
    :status 503: Redis is unavailable and a stream cannot be created.

    :responseheader Content-Type: ``text/event-stream`` for streaming responses.
    :responseheader Cache-Control: ``no-cache`` for streaming responses.
    :responseheader X-Accel-Buffering: ``no`` for streaming responses.

    :note:
        If ``smarter_settings.enable_dashboard_server_logs`` is false, the
        function returns a plain-text response and does not connect to Redis.
    """

    # either locates a user, or generates a unique job ID that is guaranteed to not have
    # any log data associated with it.
    user_context = get_user_context(request.user) if request.user.is_authenticated else job_id_factory()
    logger_prefix = logging.formatted_text(f"{__name__}.stream_user_logs()")
    logger.info("%s called", logger_prefix)

    if not smarter_settings.enable_dashboard_server_logs:
        return HttpResponse(
            "Log viewing in browser is disabled. Set environment variable "
            "'SMARTER_ENABLE_DASHBOARD_SERVER_LOGS' to make log streaming visible.",
            content_type="text/plain",
        )

    try:
        redis_cache = get_redis_connection("default")
        pubsub = redis_cache.pubsub()
        channel = build_channel(user_context)
        pubsub.subscribe(channel)
        logger.info("%s Subscribed to Redis channel '%s' for log streaming.", logger_prefix, channel)
    except RedisError:
        logger.exception("%s Failed to connect to Redis for log streaming.", logger_prefix, exc_info=True)
        return HttpResponse(
            "Log stream is temporarily unavailable.",
            content_type="text/plain",
            status=HTTPStatus.SERVICE_UNAVAILABLE,
        )

    async def event_stream():
        try:
            logger.info("%s.event_stream() Starting log stream event generator.", logger_prefix)
            # Ask the browser to retry quickly if disconnected.
            yield "retry: 3000\n\n"

            while True:
                message = await asyncio.to_thread(
                    pubsub.get_message,
                    ignore_subscribe_messages=True,
                    timeout=15.0,
                )

                if message and message.get("type") == "message":
                    raw = message.get("data", "")
                    data = raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)
                    lines = data.splitlines() or [""]
                    for line in lines:
                        yield f"data: {line}\n"
                    yield "\n"
                else:
                    # Keep idle connections alive through proxies.
                    yield ": keepalive\n\n"
        finally:
            logger.info("%s Closing Redis pubsub connection for log streaming.", logger_prefix)
            try:
                await asyncio.to_thread(pubsub.close)
            except RedisError:
                logger.exception(
                    "%s Failed to close Redis pubsub connection for log streaming.", logger_prefix, exc_info=True
                )

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
