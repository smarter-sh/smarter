"""Constants for the provider app."""

import os

namespace = "provider"
VERIFICATION_LIFETIME = 60 * 60 * 24 * 10  # 10 calendar days, expressed in seconds
VERIFICATION_LEAD_TIME = 60 * 60 * 36  # 36 hours in seconds

HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.abspath(os.path.join(HERE, "data"))
GOOGLE_SERVICE_ACCOUNT_SECRET_NAME = "google_service_account"
GOOGLE_MAPS_API_KEY_SECRET_NAME = "google_maps_api_key"
# the Tavily web search api key, which WebsearchPlugins such as smarter_project_websearch use.
TAVILY_API_KEY_SECRET_NAME = "tavily_api_key"
# the Brave Search api key, which ImageSearchPlugins such as safe_image_search, and the
# Brave WebsearchPlugin samples such as research_assistant, use.
BRAVE_SEARCH_API_KEY_SECRET_NAME = "brave_search_api_key"

BUILTIN_PROVIDER_API_KEY_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "cohere": "COHERE_API_KEY",
    "fireworks": "FIREWORKS_API_KEY",
    "googleai": "GEMINI_API_KEY",
    "metaai": "LLAMA_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "openai": "OPENAI_API_KEY",
    "togetherai": "TOGETHERAI_API_KEY",
}
"""
The environment variable of each built-in Provider's API key, which manage.py initialize_providers.

reads. Each may also be written with the ``SMARTER_`` prefix.
"""
