# -*- coding: utf-8 -*-
"""Chatbot exceptions."""


class ChatBotCustomDomainNotFound(Exception):
    """Raised when the custom domain for the chatbot is not found."""


class ChatBotCustomDomainExists(Exception):
    """Raised when the custom domain for the chatbot already exists."""
