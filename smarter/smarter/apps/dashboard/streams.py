"""
Server-Sent Events (SSE) view for streaming logs in real-time.

This view subscribes to a Redis channel where log messages are published and
streams them to the client using Server-Sent Events (SSE).
The client can listen to this stream and update the UI in real-time as new log
messages arrive.
"""

import redis
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse

from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import GLOBAL_LOG_CHANNEL


# pylint: disable=W0613
@login_required
def stream_global_logs(request):
    r = redis.Redis(host="localhost", port=6379, db=0)
    pubsub = r.pubsub()
    pubsub.subscribe(GLOBAL_LOG_CHANNEL)

    def event_stream():
        try:
            for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"].decode()
                    yield f"data: {data}\n\n"
        finally:
            pubsub.close()  # 👈 important cleanup

    if waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_LOG_VIEW_IN_BROWSER):
        return StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    else:
        return StreamingHttpResponse(
            "Log viewing in browser is disabled. Enable the waffle switch 'ENABLE_LOG_VIEW_IN_BROWSER' to make log streaming visible.",
            content_type="text/plain",
        )
