"""
The OpenAPI 3.1 document of the Smarter api, generated from Pydantic models.

The document covers the apis that the ``smarter`` cli and the SDKs call, family by family:

- the cli api (``/api/v1/cli/``), to apply, get, describe, validate and delete the resources that
  SAM manifests declare (:mod:`.cli`),
- the chat api (``/api/v1/llm-clients/{id}/config/``, ``.../prompt/`` and ``.../provider-request/``), to chat with an
  LLMClient, as JSON or as a stream of Server-Sent Events (:mod:`.chat`),
- the REST api of each resource family, one module each in :mod:`.families`, whose responses are built from each
  app's contract models, e.g. :mod:`smarter.apps.llmclient.contract.models`. Mostly reads: clients write through
  the cli api's manifests, which the brokers validate.

The package's modules:

- :mod:`.builders`: references, responses, operations and parameters, and :class:`.builders.ApiFamily`, from
  whose Django app's name each family's tag, operation ids, paths and resource words are derived.
- :mod:`.schemas`: the document's components, from the SAM models of every kind
  (:func:`smarter.apps.api.v1.contract.sam.sam_models`), the Smarter Journal api contract
  (:mod:`smarter.lib.journal.contract.models`), the Smarter Chat api contract
  (:mod:`smarter.apps.prompt.contract.models`), each family's contract models, and the models of the cli
  commands' data (:mod:`smarter.apps.api.v1.contract.models`).
- :mod:`.routes`: which routes the document covers, and why it leaves out the others.
- :mod:`.document`: the document, assembled.

A change to any of the models changes the document. ``manage.py export_api_contract`` writes it to
``openapi.json``, beside this package, and a test fails if the committed file is out of date, or if a
route of a family in :data:`.routes.DOCUMENTED_URLCONFS` is neither in the document nor in
:data:`.routes.UNDOCUMENTED_ROUTES`.

Every platform serves this document at ``/api/v1/openapi.json`` (:mod:`smarter.apps.api.v1.contract.views`;
``/docs/openapi.json`` redirects there), and renders it with Scalar at ``/docs/openapi/``. It is the platform's
only api documentation.
"""

from .builders import (
    ApiFamily,
    id_or_hashed_id,
    merge_paths,
    query,
    rest_operation,
    rest_read,
)
from .chat import chat_paths
from .cli import cli_paths
from .document import openapi_document, openapi_json, write_openapi
from .families.guardrail import guardrail_paths
from .families.llmclient import llmclient_paths
from .families.llmhost import llmhost_paths
from .families.mcpclient import mcpclient_paths
from .families.plugin import plugin_paths
from .families.provider import provider_paths
from .families.proxy import proxy_paths
from .families.secret import secret_paths
from .families.vectorstore import vectorstore_paths
from .routes import (
    DOCUMENTED_URLCONFS,
    PATH_PARAMETER_ALIASES,
    UNDOCUMENTED_ROUTES,
    UNDOCUMENTED_URLCONFS,
)
from .schemas import CHAT_MODELS, cli_schemas

__all__ = [
    "CHAT_MODELS",
    "DOCUMENTED_URLCONFS",
    "PATH_PARAMETER_ALIASES",
    "UNDOCUMENTED_ROUTES",
    "UNDOCUMENTED_URLCONFS",
    "ApiFamily",
    "chat_paths",
    "cli_paths",
    "cli_schemas",
    "guardrail_paths",
    "id_or_hashed_id",
    "llmclient_paths",
    "llmhost_paths",
    "mcpclient_paths",
    "merge_paths",
    "openapi_document",
    "openapi_json",
    "plugin_paths",
    "provider_paths",
    "proxy_paths",
    "query",
    "rest_operation",
    "rest_read",
    "secret_paths",
    "vectorstore_paths",
    "write_openapi",
]
