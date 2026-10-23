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

LLMCLIENT_LISTVIEW_CACHE_KIND = "LLMClient"
"""The LLMClient list's name in the list view cache.

See :mod:`smarter.lib.django.listview`.
"""

LLMCLIENT_LISTVIEW_CACHE_MODELS = (
    "llmclient.LLMClient",
    "llmclient.LLMClientAPIKey",
    "llmclient.LLMClientCustomDomain",
    "llmclient.LLMClientCustomDomainDNS",
    "llmclient.LLMClientExtensions",
    "llmclient.LLMClientGuardrails",
    "llmclient.LLMClientMCPClients",
    "llmclient.LLMClientPlugin",
    "guardrail.Guardrail",
    "llmtool.PluginMeta",
    "mcpclient.MCPClient",
    "orchestrator.OrchestratorHarness",
)
"""The models whose changes alter what the LLMClient list shows: the LLMClient, the rows that it.

nests, and the resources whose names it shows.
"""

CUSTOM_DOMAIN_LISTVIEW_CACHE_KIND = "LLMClientCustomDomain"
"""The Custom Domain list's name in the list view cache.

See :mod:`smarter.lib.django.listview`.
"""

CUSTOM_DOMAIN_LISTVIEW_CACHE_MODELS = (
    "llmclient.LLMClientCustomDomain",
    "llmclient.LLMClientCustomDomainDNS",
    "llmclient.LLMClient",
)
"""The models whose changes alter what the Custom Domain list shows: the domain, its DNS records and its LLMClient."""
