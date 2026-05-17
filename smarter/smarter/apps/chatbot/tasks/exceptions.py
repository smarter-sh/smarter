"""
Celery task exceptions for chatbot app.
"""

from smarter.apps.chatbot.exceptions import SmarterChatBotException


class ChatBotCustomDomainNotFound(SmarterChatBotException):
    """Raised when the custom domain for the chatbot is not found."""


class ChatBotCustomDomainExists(SmarterChatBotException):
    """Raised when the custom domain for the chatbot already exists."""


class ChatBotTaskError(SmarterChatBotException):
    """Base class for ChatBot task exceptions."""
