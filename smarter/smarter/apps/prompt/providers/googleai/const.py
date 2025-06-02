"""
This module contains constants for the GoogleAI Gemini provider.
"""

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"  # don't forget the trailing slash
PROVIDER_NAME = "googleai"
DEFAULT_MODEL = "gemini-2.0-flash"


# https://ai.google.dev/gemini-api/docs/models/gemini
VALID_CHAT_COMPLETION_MODELS = [
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash",
    "gemini-2.0-flash-8b",
    "gemini-2.0-pro",
    "aqa",
]
