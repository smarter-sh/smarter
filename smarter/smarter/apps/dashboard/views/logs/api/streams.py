"""
Mostly GitHub Copilot vibecoded SSE log streaming views for dashboard clients.

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
import json
from http import HTTPStatus
from typing import Any, AsyncIterator, Iterator, Union

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django_redis import get_redis_connection
from redis.exceptions import RedisError

from smarter.apps.account.models import get_resolved_user
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.logging.redis_log_handler import (
    build_channel,
    get_user_context,
    job_id_factory,
    stream_key,
)

logger = logging.getLogger(__name__)
STREAM_REPLAY_BATCH_SIZE = 500
STREAM_REPLAY_MAX_ENTRIES = 2000


def _decode_redis_payload(raw: Any) -> str:
    """
    Normalize Redis pubsub or stream payloads into text.

    Redis messages may be bytes or strings depending on the client configuration
    and the source of the message (Pub/Sub vs stream). This helper ensures that
    the payload is always returned as a string for consistent processing in the
    log streaming view.

    :param raw: The raw payload from Redis, which may be a bytes, bytearray, or str.
    :type raw: Any
    :return: The decoded payload as a string.
    :rtype: str
    """
    return raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)


def _iter_sse_data_frames(data: str) -> Iterator[str]:
    """
    Render one payload into SSE data frames.

    SSE frames must be sent as lines prefixed with ``data:`` and terminated by a
    blank line. If the payload contains multiple lines, each line is sent as a
    separate ``data:`` line to ensure proper rendering in SSE clients.

    :param data: The log message payload to be sent as SSE frames.
    :type data: str
    :yields: Individual lines of the payload formatted as SSE data frames, followed by a blank line.
    :rtype: Iterator[str]
    """
    lines = data.splitlines() or [""]
    for line in lines:
        yield f"data: {line}\n"
    yield "\n"


def _should_skip_stream_internal_log(payload_text: str) -> bool:
    """
    Return True when a payload is the stream endpoint logging about itself.

    These records are implementation noise for dashboard users and should not
    be forwarded back into the same terminal stream.
    """
    stream_marker = f"{__name__}.stream_user_logs()"

    if stream_marker in payload_text:
        return True

    if " DEBUG " in payload_text:
        return True

    try:
        payload_json = json.loads(payload_text)
    except (ValueError, TypeError):
        return False

    if not isinstance(payload_json, dict):
        return False

    logger_name = str(payload_json.get("logger", ""))
    level = str(payload_json.get("level", payload_json.get("levelname", ""))).upper()
    message = str(payload_json.get("message", ""))
    return logger_name == __name__ or stream_marker in message or level == "DEBUG"


async def _replay_stream_history(redis_cache: Any, channel: str) -> AsyncIterator[str]:
    """
    Replay persisted Redis stream entries as SSE frames before live Pub/Sub.

    This helper reads the Redis stream associated with the supplied log
    channel and yields each stored payload using the same SSE framing as the
    live Pub/Sub path. Entries are fetched in batches using ``XRANGE`` and a
    moving lower-bound so that the stream backlog is replayed in order without
    re-emitting previously seen entries.

    :param redis_cache:
        Redis client obtained from ``django-redis``. The client must provide
        an ``xrange`` method compatible with Redis stream reads.
    :type redis_cache: Any
    :param channel:
        Redis Pub/Sub channel name whose persisted stream mirror should be
        replayed, for example ``"logs:User.admin"``.
    :type channel: str
    :yields:
        Individual SSE frame fragments for each persisted log payload. Each
        payload is emitted as one or more ``data:`` lines followed by a blank
        line terminator.
    :rtype: AsyncIterator[str]

    :raises redis.exceptions.RedisError:
        Propagated when the underlying Redis ``XRANGE`` call fails.

    :note:
        The function stops once Redis returns an empty batch, which indicates
        there are no more persisted entries to replay before switching to the
        live Pub/Sub stream.
    """
    key = stream_key(channel)
    upper_bound = "+"
    all_entries: list[Any] = []
    replayed_entries = 0

    while replayed_entries < STREAM_REPLAY_MAX_ENTRIES:
        # Cap each XREVRANGE call to avoid fetching more than what's left in our budget.
        remaining = STREAM_REPLAY_MAX_ENTRIES - replayed_entries
        batch_size = min(STREAM_REPLAY_BATCH_SIZE, remaining)

        # Read backwards from upper_bound so we can page through history in reverse
        # without re-fetching entries we've already seen.
        entries = await asyncio.to_thread(
            redis_cache.xrevrange,
            key,
            max=upper_bound,
            min="-",
            count=batch_size,
        )
        if not entries:
            # No more entries in the stream; stop paging.
            break

        replayed_entries += len(entries)

        for entry_id, payload in entries:
            # Redis field keys may be bytes or str depending on client decode settings.
            raw = payload.get("data", payload.get(b"data", ""))
            decoded = _decode_redis_payload(raw)
            if _should_skip_stream_internal_log(decoded):
                # Advance the cursor past this entry even though we're dropping it,
                # so the next batch starts from the correct position.
                upper_bound = f"({_decode_redis_payload(entry_id)}"
                continue
            try:
                all_entries.append(json.loads(decoded))
            except (ValueError, TypeError):
                # Not valid JSON — wrap it in a plain message envelope so the client
                # always receives a consistent object shape.
                all_entries.append({"message": decoded})
            # The "(" prefix makes the bound exclusive, preventing the current entry
            # from being returned again in the next XREVRANGE call.
            upper_bound = f"({_decode_redis_payload(entry_id)}"

    all_entries.reverse()

    yield f"event: bulk\ndata: {json.dumps(all_entries)}\n\n"


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
    user = get_resolved_user(request.user)
    if not user or not user.is_authenticated:
        user_context = job_id_factory()
    else:
        user_context = get_user_context(user)
    logger_prefix = logging.formatted_text(f"{__name__}.stream_user_logs()")
    logger.info("%s called for user_context='%s'", logger_prefix, user_context)

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

    async def event_stream() -> AsyncIterator[str]:
        """
        Generator function that yields SSE frames for log streaming.

        This function first replays any persisted log entries from the Redis stream
        associated with the user's log channel, yielding each entry as SSE frames.
        After the backlog is replayed, it enters a loop that waits for new messages
        from the Redis Pub/Sub subscription. Incoming messages are also yielded as
        SSE frames. If no message is received within the Pub/Sub timeout, a keepalive
        comment is emitted to maintain the connection.

        The generator ensures that the Redis Pub/Sub connection is properly closed
        when the stream is terminated, even if exceptions occur during streaming.

        :yields:
            SSE-formatted strings representing log messages or keepalive comments.
        :rtype: AsyncIterator[str]
        """
        try:
            logger.info("%s.event_stream() Starting log stream event generator.", logger_prefix)
            # Ask the browser to retry quickly if disconnected.
            yield "retry: 3000\n\n"

            try:
                async for event in _replay_stream_history(redis_cache, channel):
                    yield event
            except RedisError:
                logger.exception("%s Failed to replay Redis stream history for log streaming.", logger_prefix)

            while True:
                message = await asyncio.to_thread(
                    pubsub.get_message,
                    ignore_subscribe_messages=True,
                    timeout=15.0,
                )

                if message and message.get("type") == "message":
                    raw = message.get("data", "")
                    decoded = _decode_redis_payload(raw)
                    if _should_skip_stream_internal_log(decoded):
                        continue
                    for frame in _iter_sse_data_frames(decoded):
                        yield frame
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
