"""Constants for the provider app."""

import os

from django.utils.translation import gettext_noop

namespace = "provider"
presentation_app_name = gettext_noop("Provider")
"""The app's name as people read it, e.g. in the Django admin.

Translated where it is shown.
"""
VERIFICATION_LIFETIME = 60 * 60 * 24 * 10  # 10 calendar days, expressed in seconds
VERIFICATION_LEAD_TIME = 60 * 60 * 36  # 36 hours in seconds

HERE = os.path.abspath(os.path.dirname(__file__))
GOOGLE_SERVICE_ACCOUNT_SECRET_NAME = "google_service_account"
GOOGLE_MAPS_API_KEY_SECRET_NAME = "google_maps_api_key"

PROVIDER_ENV_PREFIX = "APP_PROVIDER_"
"""
The prefix of the provider app's environment variables, after the optional ``SMARTER_``.

E.g. ``SMARTER_APP_PROVIDER_OPENAI_API_KEY``. The Secret that holds a key is named without it, e.g. ``openai_api_key``, the name that it had before
the variables had the prefix, and that manifests refer to.
"""

BUILTIN_PROVIDER_API_KEY_ENV_VARS = {
    "anthropic": "APP_PROVIDER_ANTHROPIC_API_KEY",
    "cohere": "APP_PROVIDER_COHERE_API_KEY",
    "fireworks": "APP_PROVIDER_FIREWORKS_API_KEY",
    "googleai": "APP_PROVIDER_GEMINI_API_KEY",
    "metaai": "APP_PROVIDER_LLAMA_API_KEY",
    "mistral": "APP_PROVIDER_MISTRAL_API_KEY",
    "openai": "APP_PROVIDER_OPENAI_API_KEY",
    "togetherai": "APP_PROVIDER_TOGETHERAI_API_KEY",
}
"""
The environment variable of each built-in Provider's API key, which manage.py initialize_providers.

reads. Each may also be written with the ``SMARTER_`` prefix.
"""
