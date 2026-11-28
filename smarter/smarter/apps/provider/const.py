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

BUILTIN_PROVIDER_API_KEY_SECRET_NAMES = {
    "anthropic": "anthropic_api_key",
    "cohere": "cohere_api_key",
    "fireworks": "fireworks_api_key",
    "googleai": "gemini_api_key",
    "metaai": "llama_api_key",
    "mistral": "mistral_api_key",
    "openai": "openai_api_key",
    "togetherai": "togetherai_api_key",
}
"""
The Smarter Secret of each built-in Provider's API key, the Smarter admin's, by the Provider's name.

The key's only source is that Secret (issue #1099): the init Job creates it from the platform's bootstrap secrets
(``manage.py initialize_bootstrap_secrets``), an admin may set it in the web console or with ``smarter apply``, and
``initialize_providers`` gives it to the Provider. No service reads the key from its environment.
"""
