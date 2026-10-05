"""Constants for the llmclient app."""

import os

namespace = "llmclient"
presentation_app_name = "LLMClient"

HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.abspath(os.path.join(HERE, "data"))
CUSTOM_DOMAINS_PATH = os.path.join(DATA_PATH, "custom-domains")
"""The built-in CustomDomain manifests, which add_builtin_custom_domains applies."""
