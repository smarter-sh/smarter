"""
Django URL patterns for the prompt web console terminal logs tab WebSocket
endpoint. This is used for the Monaco terminal emulation page

how we got here:
 - /terminal/
"""

from django.urls import re_path

from .const import namespace
from .consumers import TerminalLogConsumer

app_name = namespace


websocket_urlpatterns = [
    re_path(r"^log/$", TerminalLogConsumer.as_asgi()),  # type: ignore[arg-type]
]
