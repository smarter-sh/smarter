Smarter MCP Client
=====================

Overview
--------

The Smarter MCP Client app provides a standardized interface for connecting large
language models to external tools and services through the Model Context Protocol (MCP).
Rather than implementing provider-specific integrations for each application,
the MCP Client discovers available tools from one or more MCP servers, negotiates
their capabilities, and exposes them to the Smarter orchestration engine as managed
resources. This allows prompts and engineering loops to invoke databases, APIs,
file systems, development tools, enterprise applications, or custom services
through a consistent protocol, while Smarter remains responsible for authentication,
authorization, auditing, and execution management. By separating tool implementation
from application logic, the MCP Client enables new capabilities to be added or
updated without modifying the surrounding AI application.

The MCP Client operates as a managed integration layer between Smarter and the
external MCP ecosystem. During initialization it establishes secure sessions
with configured MCP servers, retrieves their advertised tool definitions, and
makes those tools available for controlled invocation by prompts, agents, and
workflows. Each tool invocation is executed through Smarter’s existing security,
logging, charging, and mcpclient infrastructure, ensuring that external
capabilities remain subject to the same governance and operational controls
as native Smarter resources. This architecture allows organizations to adopt
the rapidly growing ecosystem of MCP-compatible services while maintaining
centralized configuration, observability, and policy enforcement across all
AI-assisted interactions.

The Smarter MCP Client app is included in v0.15.0 and later. It enables Account
administrators to configure and manage connections to MCP servers through the
Smarter administration interface, eliminating the need to hard-code tool
integrations or distribute MCP connection details across individual applications.

.. seealso::

    - :doc:`Smarter Installation Guide <../smarter-platform/installation>`
    - :doc:`OpenAI Getting Started Guide <../smarter-framework/guides/openai-api-getting-started-guide>`

How It Works
------------

An **MCPClient** is a Smarter resource that connects to one remote MCP server. Like every
Smarter resource, it is defined by a YAML manifest, and managed with the ``smarter`` CLI:

.. code-block:: console

    smarter apply -f deepwiki.yaml
    smarter describe mcpclient deepwiki
    smarter get mcpclients
    smarter delete mcpclient deepwiki

An LLMClient uses MCPClients by listing them in its manifest's ``spec.mcpClients``:

.. code-block:: yaml

    apiVersion: smarter.sh/v1
    kind: LLMClient
    metadata:
      name: docs_assistant
    spec:
      config:
        provider: openai
        defaultModel: gpt-4o-mini
      mcpClients:
        - deepwiki
        - microsoft_learn

On each prompt, for each of the LLMClient's active MCPClients, in order of ``priority``:

1. Smarter fetches the MCP server's **catalog**: its tools, instructions and capabilities.
   The catalog is cached for the MCPClient's ``cacheTtl`` seconds, so most prompts do not
   contact the server at all.
2. Each tool that ``allowedTools`` allows is offered to the LLM as an OpenAI-compatible
   function tool, named ``mcp<id>_<tool name>``. If ``allowedResources`` is not empty, a
   ``mcp<id>_read_resource`` tool lets the LLM read the server's matching resources.
3. If ``includeInstructions`` is true, the server's instructions are added to the system prompt.
4. When the LLM calls a tool, Smarter calls it on the MCP server, and returns the result to
   the LLM. Errors, including an unreachable server, are returned to the LLM as text, so that
   it can recover.

An MCP server that cannot be reached is skipped, and reported in the prompt's Smarter
messages. It does not fail the prompt, and the failure is remembered for a minute, so that
it does not delay every prompt by its timeout.

Smarter records the result of each connection in the MCPClient's status, which ``smarter
describe`` shows: the server's name and version, the negotiated protocol version, the tools
it offers, and the last error. A Celery task refreshes every active MCPClient hourly, and
whenever its manifest is applied.

The Manifest
------------

.. code-block:: yaml

    apiVersion: smarter.sh/v1
    kind: MCPClient
    metadata:
      name: github
      description: GitHub's MCP server, read-only.
      version: 1.0.0
    spec:
      config:
        transport: http              # http (Streamable HTTP) or sse (legacy HTTP+SSE)
        endpointUrl: https://api.githubcopilot.com/mcp/
        headers: {}                  # optional, non-secret HTTP headers
        timeout: 30                  # seconds, 1 to 120
        authType: bearer_token       # none, api_key, bearer_token or oauth2
        credentials: github_personal_access_token   # the name of a Smarter Secret
        apiKeyHeader: X-API-Key      # the header that carries an api_key credential
        allowedTools:                # glob patterns. Empty means all of the server's tools
          - get_*
          - list_*
          - search_*
        allowedResources: []         # glob patterns of resource URIs. Empty means none
        includeInstructions: true
        cacheTtl: 300                # seconds, 0 disables caching
        isActive: true
        priority: 100                # lower runs first

Authentication
~~~~~~~~~~~~~~

Credentials are never written in a manifest. ``credentials`` names a Smarter Secret, which
must belong to, or be shared with, the MCPClient's owner. ``smarter describe`` renders the
Secret's name, never its value.

- ``none``: no authentication.
- ``api_key``: the Secret's value is sent in the ``apiKeyHeader`` header.
- ``bearer_token``: the Secret's value is sent as ``Authorization: Bearer <value>``.
- ``oauth2``: an OAuth access token, sent as a bearer token. Smarter does not yet perform
  the OAuth authorization flow, nor refresh tokens, so the token must be obtained elsewhere,
  and stored in the Secret.

Security
~~~~~~~~

- Only remote MCP servers are supported. The ``stdio`` transport, which would run a command
  on the Smarter server, is rejected.
- ``endpointUrl`` must be an https URL on the standard port. Every request, including
  redirects, must go to a host whose addresses are all public, so that an MCPClient cannot
  reach Smarter's internal network or a cloud metadata service.
- ``headers`` may not set credential or transport headers, such as ``Authorization``,
  ``Cookie``, ``Host`` or ``Mcp-Session-Id``.
- ``allowedTools`` limits the tools that the LLM may call. For servers with tools that write
  or delete data, prefer an allowlist of read-only tools, and a credential with read-only
  permissions.

Example Manifests
-----------------

The Smarter repository includes example manifests for popular remote MCP servers, in
``smarter/apps/mcpclient/data/mcpclients``.

.. list-table::
   :header-rows: 1
   :widths: 20 45 15 20

   * - Name
     - Description
     - Transport
     - Authentication
   * - ``asana``
     - Work with Asana tasks, projects and goals. Uses the legacy HTTP+SSE transport.
     - sse
     - oauth2
   * - ``atlassian``
     - Search and manage Jira issues and Confluence pages, with Atlassian's Remote MCP Server.
     - http
     - oauth2
   * - ``aws_knowledge``
     - Search and read AWS documentation, and check the regional availability of AWS services.
     - http
     - none
   * - ``cloudflare_docs``
     - Search Cloudflare's developer documentation.
     - http
     - none
   * - ``context7``
     - Up-to-date, version-specific documentation and code examples for programming libraries, from Upstash Context7.
     - http
     - api_key
   * - ``deepwiki``
     - AI-generated documentation for public GitHub repositories, from Cognition's DeepWiki.
     - http
     - none
   * - ``exa``
     - Web search and web page retrieval, from Exa.
     - http
     - none
   * - ``github``
     - Read and manage GitHub repositories, issues and pull requests, with GitHub's official MCP server.
     - http
     - bearer_token
   * - ``gitmcp``
     - Documentation and code search for any public GitHub repository, from GitMCP.
     - http
     - none
   * - ``hugging_face``
     - Search the Hugging Face Hub for models, datasets and Spaces.
     - http
     - bearer_token
   * - ``linear``
     - Find, create and update Linear issues, projects and comments.
     - http
     - oauth2
   * - ``microsoft_learn``
     - Search and read Microsoft's official documentation and code samples on Microsoft Learn.
     - http
     - none
   * - ``neon``
     - Manage Neon serverless Postgres projects, branches and databases.
     - http
     - bearer_token
   * - ``notion``
     - Search, read and write Notion pages and databases, with Notion's hosted MCP server.
     - http
     - oauth2
   * - ``sentry``
     - Investigate Sentry issues, errors and performance data.
     - http
     - oauth2
   * - ``square``
     - Query Square payments, orders, catalog and customers. Uses the legacy HTTP+SSE transport.
     - sse
     - oauth2
   * - ``stripe``
     - Query Stripe customers, products, prices, invoices and payments, with Stripe's official MCP server.
     - http
     - bearer_token
   * - ``supabase``
     - Query and manage Supabase projects, databases and edge functions.
     - http
     - bearer_token

For example, DeepWiki's MCP server requires no authentication:

.. literalinclude:: ../../../smarter/smarter/apps/mcpclient/data/mcpclients/deepwiki.yaml
    :language: yaml

and GitHub's requires a personal access token:

.. literalinclude:: ../../../smarter/smarter/apps/mcpclient/data/mcpclients/github.yaml
    :language: yaml

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental.

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   mcpclient/api
   mcpclient/caching
   mcpclient/connection
   mcpclient/const
   mcpclient/exceptions
   mcpclient/manifest
   mcpclient/models
   mcpclient/receivers
   mcpclient/serializers
   mcpclient/signals
   mcpclient/tasks
   mcpclient/toolkit
   mcpclient/views
