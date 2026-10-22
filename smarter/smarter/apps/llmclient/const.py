"""Constants for the llmclient app."""

import os

namespace = "llmclient"
presentation_app_name = "LLMClient"

HERE = os.path.abspath(os.path.dirname(__file__))
EXAMPLE_MANIFESTS_REPOSITORY_URL = "https://github.com/smarter-sh/example-manifests"
"""
The community-supported collection of example manifests, one folder per kind.

Its Guardrails, CustomDomain, Budgets, MCPClients, LLMHostComputes, LLMHosts, Proxies, Vectorstores,
plugins and LLMClients. ``manage.py load_from_github`` applies all of them for the Smarter admin in
``manage.py initialize_platform``, and the plugins and LLMClients for each account's admin in
``manage.py initialize_account``.
"""
STACKADEMY_REPOSITORY_URL = "https://github.com/smarter-sh/stackademy"
"""
The Stackademy project: the manifests of the fictional Stackademy code academy's AI resources.

Its Secrets, Connections, plugins, LLMClients and Budget. ``manage.py load_from_github`` applies
them, for the Smarter admin in ``manage.py initialize_platform``, and for each account's admin in
``manage.py initialize_account``. ``manage.py verify_stackademy`` prompts its LLMClients.
"""
