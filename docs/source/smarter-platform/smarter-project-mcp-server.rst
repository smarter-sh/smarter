Smarter Project MCP Server
==========================

Every Smarter platform runs a `Model Context Protocol <https://modelcontextprotocol.io>`__
server, over Streamable HTTP, for The Smarter Project. It does two things:

- **Technical questions.** It answers questions about Smarter from its own source code,
  documentation and blog, and checks the manifests that an LLM writes against the platform's own
  validation. Anyone may use it, without authentication.
- **GitHub operations.** It searches the project's GitHub issues, and, for a user who sends
  their own GitHub token, opens issues and comments on them under that user's account. See
  `GitHub Issues`_.

It reads every public repository of the `smarter-sh <https://github.com/smarter-sh>`__ GitHub organization: the
platform and its documentation, the command-line interface, the Python, Node.js and Go SDKs,
the VS Code extension, the SmarterChat component, the quick start, the cloud infrastructure,
the example manifests, Stackademy, the Smarter Chat integrations for WordPress, Drupal, Shopify,
Google Tag Manager and documentation sites, the extension registry and its official extensions,
and the cache-results and smarter-types packages. It also reads the project's blog, `blog.smarter.sh <https://blog.smarter.sh>`__,
whose release announcements and articles explain what changed in each version, and how and why
Smarter was built.

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
     - Every repository, and the blog. Each repository tool takes a ``repository`` argument, and
       the search tools search every repository when it is omitted.
   * - ``/api/v1/mcp/smarter-project/<repository>/``
     - One repository, e.g. ``/api/v1/mcp/smarter-project/smarter-cli/``. The tools have no
       ``repository`` argument, and the blog's tools are not served.

The repositories are ``smarter``, ``smarter-cli``, ``smarter-python``, ``smarter-nodejs``,
``smarter-golang``, ``smarter-vscode-yaml``, ``smarter-infrastructure``, ``smarter-deploy``,
``example-manifests``, ``stackademy``, ``smarter-wordpress``, ``smarter-drupal``,
``smarter-shopify``, ``smarter-gtm-template``, ``smarter-docs-site-generators``,
``extensions-registry``, ``smarter-extension-calculator``, ``smarter-extension-date-calculator``,
``smarter-extension-weather``, ``cache-results`` and ``smarter-types``, as declared in
:mod:`smarter.apps.mcpserver.repositories`. ``smarter`` includes Smarter Chat, the
``@smarter.sh/ui-chat`` npm package.

The server requires no authentication. Its tools read public repositories, except
``create_issue`` and ``comment_on_issue``, which a client gets only by sending the user's own
GitHub token: see `GitHub Issues`_. It is stateless: it answers every POST with ``application/json``, issues no ``Mcp-Session-Id``, and
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

Every tool but ``create_issue`` and ``comment_on_issue`` is read-only, and returns Markdown, with links to the file on GitHub, at the indexed
commit, and, for a page of the Sphinx documentation, to the page on docs.smarter.sh. The blog's
tools link to the post.

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
   * - ``get_manifest_schema``
     - A resource kind's example manifest, in YAML, and every field of its manifest: its path, type,
       whether it is required, its default and its description. Without a kind, the list of kinds.
       Every server serves it.
   * - ``validate_manifest``
     - Validates a manifest, in YAML or JSON, with the platform's own validation, without applying
       it: whether it is valid, and each error with the path of its field. Every server serves it.
   * - ``search_blog``
     - Ranked passages of the blog's posts. Only the server of every repository serves it.
   * - ``read_blog_post``
     - A post of the blog, by its path or url, with line numbers, 400 lines at a time.
   * - ``search_issues``
     - The GitHub issues of a repository, or of every repository, live from GitHub's search: their
       state, number of comments and url, best match first, optionally only ``open`` or ``closed``.
   * - ``create_issue``
     - Opens a GitHub issue in a repository, with a ``title`` and a Markdown ``body``, under the
       user's own GitHub account, and returns its url. Served only to a request that carries the
       user's GitHub token. See `GitHub Issues`_.
   * - ``comment_on_issue``
     - Adds a Markdown comment to an issue, by its ``issue_number``, under the user's own GitHub
       account. Served only with the user's GitHub token.

``get_manifest_schema`` reads the platform's own JSON Schemas and example manifests, which are
committed with the :doc:`api contract </smarter-framework/smarter-api/api-contract>`, so it
describes exactly the manifests that the platform accepts. A schema is too large and nested for
an LLM to read well, so :func:`smarter.apps.mcpserver.manifests.schemas.manifest_fields` flattens it into
one line per field, without the read-only ``status``. The server's instructions tell the LLM to
call it before writing, fixing or explaining a manifest.

``validate_manifest`` then checks the manifest that the LLM wrote, with
:func:`smarter.apps.api.v1.cli.validation.validate_manifest`, the validation of ``smarter
validate`` and the first step of ``smarter apply``, and the server's instructions tell the LLM to
fix what it reports before it gives the manifest to the user. Because anyone may call it, it skips
the checks that make requests, e.g. that an image url responds, and refuses YAML aliases and
manifests longer than 50,000 characters. A valid manifest may still be refused by ``apply`` for
something outside of it, e.g. a Secret that it names does not exist.

A search ranks files in the database, without embeddings. A quoted phrase is one search term,
and so is an identifier such as ``smarter_settings.environment_platform_domain``. Each term counts
for more the rarer it is, and a term in a file's path or title counts for more than one in its
text. See :mod:`smarter.apps.mcpserver.index.search`.

The server's instructions, which MCPClients with ``includeInstructions: true`` add to the
LLM's system prompt, tell the LLM to answer from the tools rather than from memory, and to cite
its sources. The server of every repository also tells it to search the blog together with the
documentation for why and how questions, e.g. how the platform keeps passwords out of its logs,
because a post often explains a design, and its limits, more completely than the reference
documentation does.

The Index
---------

The server reads its own index of the repositories, in the platform's database, rather than
GitHub, so that a tool call costs one or two queries. :func:`smarter.apps.mcpserver.index.indexer.index_repository`
keeps each repository's index up to date with its ``main`` branch:

1. It asks the GitHub api for the branch's latest commit. A repository that has not changed costs
   this one small request, so the hourly refresh of all 21 repositories, 21 requests, stays within
   GitHub's limit of 60 unauthenticated requests an hour for each IP address.
2. Otherwise, it downloads the repository's archive at that commit, and reads its text files in
   memory, without extracting anything to disk. It keeps documentation and source code, and
   skips binaries, vendored and generated files, lock files, and files larger than 256 KB. Each
   ``image`` and ``figure`` directive of a repository's published Sphinx documentation gets the
   image's published url, as a Markdown image whose description is its ``:alt:``, on the same
   line, so that the LLM can show it, and line numbers still match the file on GitHub.
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

The blog is indexed the same way, by :func:`smarter.apps.mcpserver.index.blog.index_blog`, from its
public WordPress REST api, ``/wp-json/wp/v2/posts``, 100 posts a request. Each published post
becomes one file of the index, its html converted to Markdown-like text, under its permalink's
path, e.g. ``2026/10/26/release-smarter-api-v0-6``. Its illustrations become Markdown images,
``![description](url)``, followed by their full alt text, which is what tells the LLM what an
image shows. The server's instructions tell the LLM to include an illustration in its answer
when it shows what the user asked about, and Smarter Chat displays it. The posts are fingerprinted by their ids and
modification times, and a blog whose posts have not changed is not stored again.
:func:`~smarter.apps.mcpserver.tasks.index_repositories` queues it with the repositories, and
``--blog`` indexes only the blog:

.. code-block:: console

    python manage.py index_smarter_project --blog --force

The indexes are the ``RepositoryIndex`` and ``RepositoryFile`` rows of the Django admin's
*MCPServer* app, which shows each repository's commit, file count and last error.

Because the data changes only when an index does, each tool call's result is cached for an hour, by
the server, the tool and its arguments, so a repeated search or read costs no query at all. A
repository or blog that is indexed again starts a new index generation, which is part of every
cached result's key, so new files and posts are found at once rather than an hour later. Errors are
never cached. See :mod:`smarter.apps.mcpserver.caching`. The server marks every tool but
``create_issue`` and ``comment_on_issue`` read-only, so an MCPClient that calls it caches the
results on its side too.

GitHub Issues
-------------

``search_issues`` finds the known bugs and feature requests of The Smarter Project, and whether
they are fixed, from GitHub's issue search, live rather than from the index, because issues change
by the minute. Its results are cached for a minute. It searches one repository with ``repo:``, or
every repository with ``org:smarter-sh``. Anyone may call it: a request without a GitHub token
searches anonymously, and GitHub allows anonymous clients 10 searches a minute for each IP address,
which the platform's users share, so a busy platform's anonymous searches may be refused for a
minute. A classic token, when the client sends one, raises that limit to 30 for its owner. See
:mod:`smarter.apps.mcpserver.github.issues`.

``create_issue`` lets an LLM report a bug or request a feature in a repository of The Smarter
Project, e.g. after it has found the cause of a problem in the code, and ``comment_on_issue`` lets it
add to an existing issue instead, e.g. another way to reproduce a bug. The server's instructions
tell the LLM to call ``search_issues`` first, and to comment rather than open an issue twice. Both
write as the user, with the user's own GitHub classic personal access token. The platform holds no
GitHub credential that can write: the issue or comment is the user's, GitHub decides what the user
may do, and its own limits apply.

The client sends the token in an ``Authorization: Bearer`` header. A request without one is not
offered ``create_issue`` or ``comment_on_issue`` at all. Create the token at `github.com/settings/tokens
<https://github.com/settings/tokens>`__, as a classic token with only the ``public_repo`` scope, and
give it an expiration date. A classic token cannot be limited to one repository: with
``public_repo``, it can write to every public repository that you can write to, so keep it secret.
A fine-grained token, ``github_pat_...``, is refused, because it can write only to the repositories
of the account or organization that it was created for.

With Claude Code:

.. code-block:: console

    claude mcp add --transport http smarter-project https://platform.example.com/api/v1/mcp/smarter-project/ \
      --header "Authorization: Bearer ghp_..."

With an MCPClient, set ``authType: bearer_token``, and put the token in a :doc:`Secret
<../smarter-resources/smarter-secret>` that ``credentials`` names. The built-in MCPClients send no
token, so the LLMClients that use them cannot write issues. An MCPClient that is shared writes every
issue and comment under the account of its Secret's token.

The server sends the token only to ``api.github.com``, and never logs, caches or stores it, nor
passes it to the LLM. ``search_issues`` sends only a classic token, so that a secret that is not
GitHub's never reaches GitHub. ``create_issue`` and ``comment_on_issue`` are annotated as tools that
write, so MCP clients may ask the user before they call them, and their results are never cached,
by the server or by an MCPClient. The server's instructions tell the LLM to call them only when the
user asks, after showing them exactly what it will write. Each issue and comment ends with a line
that says it was written with the Smarter Project MCP server. GitHub's errors, e.g. a token without
the ``public_repo`` scope, a locked issue, or a repository whose issues are turned off, are
explained to the LLM. See :mod:`smarter.apps.mcpserver.github.client` and
:mod:`smarter.apps.mcpserver.github.issues`.

The Built-in MCPClients
-----------------------

The ``smarter_project`` and ``smarter_project_github*`` MCPClients, which ``manage.py
initialize_platform`` applies from the :doc:`example manifests repository
</smarter-framework/smarter-manifests/example-manifests>`, read the MCP server of the platform that
applies them. Their manifests, in its ``mcp-clients/`` folder, are templates, ``*.yaml.tpl``, whose
``endpointUrl`` is filled in when they are applied:

.. code-block:: yaml

    endpointUrl: ${environment_platform_scheme}://${environment_platform_domain}/api/v1/mcp/smarter-project/smarter-cli/

``environment_platform_domain`` is ``smarter_settings.environment_platform_domain``, e.g.
``alpha.platform.example.com``, and ``environment_platform_scheme`` is the scheme of
``smarter_settings.environment_url``, ``https``. In local development, they are ``http`` and
``localhost:9357``. An MCPClient may connect to a loopback host only in the local environment:
see :func:`smarter.apps.mcpclient.connection.validate_endpoint_url`.

.. literalinclude:: /_example-manifests/mcp-clients/smarter-project.yaml.tpl
    :language: yaml

From `mcp-clients/smarter-project.yaml.tpl <https://github.com/smarter-sh/example-manifests/blob/main/mcp-clients/smarter-project.yaml.tpl>`__ in the :doc:`example manifests repository </smarter-framework/smarter-manifests/example-manifests>`.

The example LLMClients ``smarter_developer``, which helps developers understand and contribute to
the platform, and ``smarter_sdk_guide``, which helps programmers call it from Python, Node.js, Go
and the command line, are built on them, in its ``llm-clients/`` folder.

.. note::

    **Experimental.** The Smarter Project MCP server was designed and coded by Claude Code
    (Anthropic's Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental.

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1
   :caption: Protocol

   smarter-project-mcp-server/views
   smarter-project-mcp-server/server
   smarter-project-mcp-server/tools

.. toctree::
   :maxdepth: 1
   :caption: Index

   smarter-project-mcp-server/indexer
   smarter-project-mcp-server/blog
   smarter-project-mcp-server/search
   smarter-project-mcp-server/index-tools

.. toctree::
   :maxdepth: 1
   :caption: Manifests

   smarter-project-mcp-server/manifests
   smarter-project-mcp-server/manifest-tools

.. toctree::
   :maxdepth: 1
   :caption: GitHub

   smarter-project-mcp-server/github
   smarter-project-mcp-server/issues
   smarter-project-mcp-server/github-tools

.. toctree::
   :maxdepth: 1
   :caption: Shared

   smarter-project-mcp-server/repositories
   smarter-project-mcp-server/models
   smarter-project-mcp-server/tasks
   smarter-project-mcp-server/signals
   smarter-project-mcp-server/receivers
   smarter-project-mcp-server/ratelimit
   smarter-project-mcp-server/exceptions
