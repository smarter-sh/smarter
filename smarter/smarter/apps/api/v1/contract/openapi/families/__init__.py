"""
The REST api's families of routes, one module per family.

Each module declares its family, an :class:`~smarter.apps.api.v1.contract.openapi.builders.ApiFamily` named
after its Django app, and a ``<family>_paths()`` function that returns its operations. :data:`FAMILIES` lists
them in the order of the document's tags.
"""

from smarter.apps.api.v1.contract.openapi.builders import ApiFamily

from .account import ACCOUNTS
from .extension import EXTENSIONS
from .guardrail import GUARDRAILS
from .history import HISTORY
from .journal import JOURNAL
from .llmclient import LLMCLIENTS
from .llmhost import LLMHOSTS
from .mcpclient import MCPCLIENTS
from .orchestrator import ORCHESTRATORS
from .plugin import PLUGINS
from .provider import PROVIDERS
from .proxy import PROXIES
from .secret import SECRETS
from .vectorsearch import VECTORSEARCHES
from .vectorstore import VECTORSTORES

FAMILIES: tuple[ApiFamily, ...] = (
    LLMCLIENTS,
    GUARDRAILS,
    SECRETS,
    MCPCLIENTS,
    VECTORSTORES,
    LLMHOSTS,
    PLUGINS,
    PROVIDERS,
    PROXIES,
    ACCOUNTS,
    HISTORY,
    JOURNAL,
    ORCHESTRATORS,
    VECTORSEARCHES,
    EXTENSIONS,
)
"""Every family that the document covers, in the order of the document's tags."""

__all__ = [
    "ACCOUNTS",
    "EXTENSIONS",
    "FAMILIES",
    "GUARDRAILS",
    "HISTORY",
    "JOURNAL",
    "LLMCLIENTS",
    "LLMHOSTS",
    "MCPCLIENTS",
    "ORCHESTRATORS",
    "PLUGINS",
    "PROVIDERS",
    "PROXIES",
    "SECRETS",
    "VECTORSEARCHES",
    "VECTORSTORES",
]
