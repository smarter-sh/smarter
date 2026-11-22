"""Constants for the prompt app."""

import os

from django.utils.translation import gettext_noop

namespace = "prompt"
presentation_app_name = gettext_noop("Prompt")
"""The app's name as people read it, e.g. in the Django admin.

Translated where it is shown.
"""
HERE = os.path.abspath(os.path.dirname(__file__))


SMARTER_EXAMPLE_LLM_CLIENT_NAME = "example"
"""The name of the example LLMClient, which ``manage.py seed_chat_history`` seeds a chat history for."""

SMARTER_CHAT_SESSION_KEY_NAME = "session_key"
"""
The name of a chat's session key: a Prompt's field, the chat api's parameter, and the browser cookie.

The web console and Smarter Chat have the same name in their own constants, which must stay in sync.
"""
