Smarter Project MCP Server
==========================

Every Smarter platform runs an MCP server that answers questions about The Smarter Project
from its own source code and documentation. It is a `Model Context Protocol
<https://modelcontextprotocol.io>`__ server, over Streamable HTTP, that reads every public
repository of the `smarter-sh <https://github.com/smarter-sh>`__ GitHub organization: the
platform and its documentation, the command-line interface, the Python, Node.js and Go SDKs,
the VS Code extension, the SmarterChat component, the quick start, and the cloud
infrastructure.

Its main clients are the platform's own built-in :doc:`MCPClients <../smarter-resources/smarter-mcpclient>`,
``smarter_project`` and ``smarter_project_github*``, which give LLMClients such as ``smarter``,
``smarter_developer`` and ``smarter_sdk_guide`` their answers about Smarter. Any other MCP client
can use it too, e.g. Claude Code, an IDE, or another platform's MCPClient.

It is an internal platform service, not a resource: there is no manifest to apply, and
nothing to configure.

Endpoints
---------

The server is mounted under ``/api/v1/mcp/`` of the platform's own domain:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Endpoint
     - Reads
   * - ``/api/v1/mcp/smarter-project/``
     - Every repository. Each tool takes a ``repository`` argument, and the search tools search
       every repository when it is omitted.
   * - ``/api/v1/mcp/smarter-project/<repository>/``
     - One repository, e.g. ``/api/v1/mcp/smarter-project/smarter-cli/``. The tools have no
       ``repository`` argument.

The repositories are ``smarter``, ``smarter-cli``, ``smarter-python``, ``smarter-nodejs``,
``smarter-golang``, ``smarter-vscode-yaml``, ``smarter-infrastructure``, ``smarter-chat`` and
``smarter-deploy``, as declared in :mod:`smarter.apps.mcpserver.repositories`.

The server requires no authentication. It is read-only, and serves public repositories. It is
stateless: it answers every POST with ``application/json``, issues no ``Mcp-Session-Id``, and
answers GET and DELETE with ``405 Method Not Allowed``, so any of the platform's pods can answer
any request. It speaks the ``initialize`` handshake of protocol versions 2024-11-05 through
2025-11-25.

Because it requires no authentication, each client IP address may send at most
``SMARTER_MCPSERVER_RATE_LIMIT`` requests a minute, 1200 by default, and is answered ``429 Too
Many Requests``, with a ``Retry-After`` header, beyond that. The platform's own MCPClients count
too: they connect from the platform's egress addresses, and each tool call is about three
requests, so a busy platform may need a higher limit. ``0`` disables it. See
:mod:`smarter.apps.mcpserver.ratelimit`.

To try it, list its tools with curl:

.. code-block:: console

    curl -s https://platform.example.com/api/v1/mcp/smarter-project/smarter-cli/ \
      -H "Content-Type: application/json" \
      -H "Accept: application/json, text/event-stream" \
      -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'

or add it to Claude Code:

.. code-block:: console

    claude mcp add --transport http smarter-project https://platform.example.com/api/v1/mcp/smarter-project/

Tools
-----

Every tool is read-only, and returns Markdown, with links to the file on GitHub, at the indexed
commit, and, for a page of the Sphinx documentation, to the page on docs.smarter.sh.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Tool
     - What it does
   * - ``get_repository_overview``
     - What a repository contains, its GitHub url, its indexed commit, its top-level folders and
       files, and its README. Without a repository, a table of every repository.
   * - ``search_documentation``
     - Ranked passages of the documentation: the Sphinx sources in ``docs/source``, READMEs, and
       other reStructuredText and Markdown files.
   * - ``search_code``
     - Ranked files of source code and configuration, with their matching lines, optionally under
       a ``path``.
   * - ``read_file``
     - A file, with line numbers, 400 lines at a time, from ``start_line`` to ``end_line``.
   * - ``list_files``
     - The folders, with their number of files, and the files in a folder.

A search ranks files in the database, without embeddings. A quoted phrase is one search term,
and so is an identifier such as ``smarter_settings.environment_platform_domain``. Each term counts
for more the rarer it is, and a term in a file's path or title counts for more than one in its
text. See :mod:`smarter.apps.mcpserver.search`.

The server's instructions, which MCPClients with ``includeInstructions: true`` add to the
LLM's system prompt, tell the LLM to answer from the tools rather than from memory, and to cite
its sources.

The Index
---------

The server reads its own index of the repositories, in the platform's database, rather than
GitHub, so that a tool call costs one or two queries. :func:`smarter.apps.mcpserver.indexer.index_repository`
keeps each repository's index up to date with its ``main`` branch:

1. It asks the GitHub api for the branch's latest commit. A repository that has not changed costs
   this one small request, so the hourly refresh of every repository stays well within GitHub's
   limit of 60 unauthenticated requests an hour.
2. Otherwise, it downloads the repository's archive at that commit, and reads its text files in
   memory, without extracting anything to disk. It keeps documentation and source code, and
   skips binaries, vendored and generated files, lock files, and files larger than 256 KB.
3. It replaces the repository's files in one transaction, so that a search never sees a partial
   index. If indexing fails, the existing index is kept, and the failure is recorded in the
   index's ``error``.

Celery Beat runs :func:`~smarter.apps.mcpserver.tasks.index_repositories` hourly, on the
platform's operational queue, and ``manage.py initialize_platform`` queues it, so a new platform
is indexed within minutes of being initialized. A tool that is called on a repository that is not
indexed yet says so, and queues the repository. To index the repositories now:

.. code-block:: console

    python manage.py index_smarter_project
    python manage.py index_smarter_project --repository smarter-cli --force
    python manage.py index_smarter_project --queue

The indexes are the ``RepositoryIndex`` and ``RepositoryFile`` rows of the Django admin's
*MCPServer* app, which shows each repository's commit, file count and last error.

The Built-in MCPClients
-----------------------

The ``smarter_project`` and ``smarter_project_github*`` MCPClients that ``manage.py
add_builtin_mcpclients`` applies read the MCP server of the platform that applies them. Their
manifests, in ``smarter/apps/mcpclient/data/mcpclients``, are templates, ``*.yaml.tpl``, whose
``endpointUrl`` is filled in when they are applied:

.. code-block:: yaml

    endpointUrl: ${environment_platform_scheme}://${environment_platform_domain}/api/v1/mcp/smarter-project/smarter-cli/

``environment_platform_domain`` is ``smarter_settings.environment_platform_domain``, e.g.
``alpha.platform.example.com``, and ``environment_platform_scheme`` is the scheme of
``smarter_settings.environment_url``, ``https``. In local development, they are ``http`` and
``localhost:9357``. An MCPClient may connect to a loopback host only in the local environment:
see :func:`smarter.apps.mcpclient.connection.validate_endpoint_url`.

.. literalinclude:: ../../../smarter/smarter/apps/mcpclient/data/mcpclients/smarter-project.yaml.tpl
    :language: yaml

The example LLMClients ``smarter_developer``, which helps developers understand and contribute to
the platform, and ``smarter_sdk_guide``, which helps programmers call it from Python, Node.js, Go
and the command line, are built on them, in ``smarter/apps/llmclient/data/llm-clients``.

.. note::

    **Experimental.** The Smarter Project MCP server was designed and coded by Claude Code
    (Anthropic's Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental.

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   smarter-project-mcp-server/exceptions
   smarter-project-mcp-server/indexer
   smarter-project-mcp-server/models
   smarter-project-mcp-server/ratelimit
   smarter-project-mcp-server/receivers
   smarter-project-mcp-server/repositories
   smarter-project-mcp-server/search
   smarter-project-mcp-server/server
   smarter-project-mcp-server/signals
   smarter-project-mcp-server/tasks
   smarter-project-mcp-server/tools
   smarter-project-mcp-server/views
