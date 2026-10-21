"""Constants for the llmclient app."""

import os

namespace = "llmclient"
presentation_app_name = "LLMClient"

HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.abspath(os.path.join(HERE, "data"))
CUSTOM_DOMAINS_PATH = os.path.join(DATA_PATH, "custom-domains")
"""The built-in CustomDomain manifests, which add_example_custom_domains applies."""
EXAMPLE_LLMCLIENTS_PATH = os.path.join(DATA_PATH, "llm-clients")
"""The example LLMClient manifests, which ``manage.py add_example_llmclients`` applies, and ``deploy_example_llmclients`` deploys."""
STACKADEMY_REPOSITORY_URL = "https://github.com/smarter-sh/stackademy"
"""
The Stackademy project: the manifests of the fictional Stackademy code academy's AI resources.

Its Secrets, Connections, plugins, LLMClients and Budget. ``manage.py load_from_github`` applies
them, for the Smarter admin in ``manage.py initialize_platform``, and for each account's admin in
``manage.py initialize_account``. ``manage.py verify_stackademy`` prompts its LLMClients.
"""
