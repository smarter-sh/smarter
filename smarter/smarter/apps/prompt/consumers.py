"""
Consumers for the prompt app web console terminal logs tab, which handle
WebSocket connections for real-time terminal logs and interactions.
"""

from channels.generic.websocket import AsyncWebsocketConsumer


class TerminalLogConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for handling real-time terminal logs.
    """

    async def connect(self):
        await self.accept()
