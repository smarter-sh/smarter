"""
Consumers for the prompt app web console terminal logs tab, which handle
WebSocket connections for real-time terminal logs and interactions.

.. note::

    This module is currently reserved for future use in case bi-directional
    communication is needed between the terminal emulator React component and
    the Django backend.
"""

from channels.generic.websocket import AsyncWebsocketConsumer

from smarter.common.mixins import SmarterHelperMixin
from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)


class RedisLogConsumer(AsyncWebsocketConsumer, SmarterHelperMixin):
    """
    WebSocket consumer for handling real-time terminal logs.
    """

    async def connect(self):
        await self.accept()
        logger.info("%s.connect() Client connected to WebSocket endpoint.", self.formatted_class_name)


urlpatterns = []

__all__ = ["urlpatterns"]
