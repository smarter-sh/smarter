"""
Server-Sent Events (SSE) view for streaming logs in real-time.

This view subscribes to a Redis channel where log messages are published and
streams them to the client using Server-Sent Events (SSE).
The client can listen to this stream and update the UI in real-time as new log
messages arrive.
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
    Stream log messages for the authenticated user in real-time using Server-Sent Events (SSE).

    :param request: The HTTP request object from the client.
    :return: A StreamingHttpResponse that streams log messages or an HttpResponse if streaming is unavailable.
    :rtype: Union[StreamingHttpResponse, HttpResponse]
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
