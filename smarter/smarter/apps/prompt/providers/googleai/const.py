"""
This module contains constants for the GoogleAI Gemini provider.
"""

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"  # don't forget the trailing slash
PROVIDER_NAME = "googleai"
DEFAULT_MODEL = "gemini-flash-latest"


# https://ai.google.dev/gemini-api/docs/models
VALID_CHAT_COMPLETION_MODELS = [
    "gemini-flash-latest",
    "gemini-3-pro-preview",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]
