Extensibility
=============

An LLM knows only what it was trained on, and what is in its prompt. An application can give it
everything else in two ways:

- **Retrieval-augmented generation (RAG).** The application searches its own content, and adds
  what it finds to the prompt as the conversation goes on, whether or not the LLM needs it.
  Smarter takes the commonly accepted approach, a vector search: see
  :doc:`Vectorsearch <../smarter-resources/smarter-vectorsearch>`.
- **Tool calling**, a feature of most modern LLMs. The LLM decides for itself what it needs:
  today's weather, a customer's order, a row in your database, a calculation it would otherwise
  guess at. The application offers the LLM a list of tools, the LLM asks to call one, the
  application runs it and returns the result, and the LLM writes its answer from that result.

Tools are usually the better choice for live data, actions and calculations, and they are what
this page is about. Smarter offers the LLM the tools that an LLMClient lists, and runs the ones
the LLM calls.

.. seealso::

    :doc:`../smarter-resources/llmtool/how-tools-work`, for how tool calling works with any
    OpenAI-compatible API.

Smarter has three ways to add tools to a prompt: two for tools that Smarter runs itself, configured or
coded, and one for tools that a third party service provides.

**Plugins** are declarative and are proprietary to Smarter.
A prompt engineer writes a YAML manifest that configures one of
Smarter's built-in tool patterns: answer from static data, run a SQL query, call a REST API,
follow a skill, search the web, or search for images. Plugins are
:doc:`SAM resources <smarter-manifests>`, applied with the ``smarter`` CLI or the API, owned by
an account, and shared like any other resource. No code is written or installed.

**Extensions** are code. While the code itself is not proprietary to Smarter, the
way that its packaged and delivered to the LLM is. A Python developer writes a package whose tools do whatever Python can
do, packages it as a zip archive, and publishes it to the Smarter Extension registry. A platform
administrator installs it at run time, from the web console, much as a WordPress
administrator installs a plugin. Every LLMClient on the platform can then list it.

**MCP servers** are someone else's entirely, but Smarter supports this popular protocol.
Many services already publish their tools through the
Model Context Protocol. An **MCPClient** is a SAM manifest that connects to one such remote
server, and Smarter offers its tools to the LLM and calls them on that server. No code is
written, and none of it runs on Smarter. See :doc:`../smarter-resources/smarter-mcpclient`.

Plugins, Extensions and MCP Servers Compared
--------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 19 27 27 27

   * -
     - Plugins
     - Extensions
     - MCP servers
   * - What it is
     - A SAM manifest that configures a built-in tool pattern
     - A Python package with its own tools, settings, documentation and lifecycle
     - An MCPClient: a SAM manifest that connects to a remote MCP server
   * - Written by
     - Prompt engineers, in YAML
     - Python developers
     - An organization, like Netflix or GitHub or YouTube, that publishes an MCP server
   * - Installed by
     - Any user, with ``smarter apply``
     - A platform superuser, from the web console, by upload or from the registry
     - Any user, with ``smarter apply``
   * - Scope
     - Owned by a user, shared within an account
     - Platform-wide, available to every account or to listed accounts
     - Owned by a user, shared within an account
   * - Can do
     - What its pattern does: static data, SQL, REST APIs, skills, web and image search
     - Anything Python can do, with the platform's code and libraries
     - Whatever the server's tools do, limited by ``allowedTools``
   * - Configuration
     - In its manifest, with credentials in Secrets and Connections
     - Settings that the administrator configures, with credentials in Secrets
     - In its manifest, with credentials in Secrets
   * - Selection
     - Offered when a prompt matches its selector's search terms
     - Offered on every prompt of an LLMClient that lists it
     - Offered on every prompt of an LLMClient that lists it
   * - Listed in an LLMClient's
     - ``spec.plugins``
     - ``spec.extensions``
     - ``spec.mcpClients``
   * - Lives in
     - ``smarter.apps.llmtool.plugin``
     - ``smarter.apps.llmtool.extension``
     - ``smarter.apps.mcpclient``
   * - Distribution
     - Manifests, in source control or the API
     - Zip archives, from the signed Smarter Extension registry or uploaded
     - Manifests, in source control or the API
   * - Trust
     - Runs inside Smarter's own, reviewed tool patterns
     - Runs arbitrary code with full access to the platform: install only what you trust
     - Runs on the remote server, which sees the LLM's arguments: connect only to servers you trust

Choose a Plugin when one of the built-in patterns does the job: it takes minutes, needs no
deployment, and anyone in an account can manage it. Choose an Extension when it doesn't, for
example to geocode an address and query a weather service, to compute rather than look up, or
to integrate a service whose API needs more than a REST call. Choose an MCP server when the
service you want already publishes one: GitHub, Atlassian, AWS documentation and many others
do, and Smarter includes example MCPClient manifests for them.

All three kinds of tool appear side by side in an LLMClient's manifest:

.. code-block:: yaml

    apiVersion: smarter.sh/v1
    kind: LLMClient
    metadata:
      name: travel_assistant
      description: A travel assistant that knows today's weather.
      version: 1.0.0
    spec:
      config:
        prompt:
          provider: openai
          defaultSystemRole: You are a helpful travel assistant.
      extensions:
        - weather
      plugins:
        - travel_destinations
      mcpClients:
        - exa

Where to Go Next
----------------

.. grid:: 1 1 3 3
   :gutter: 2

   .. grid-item-card:: Administrators
      :link: ../smarter-platform/extensions
      :link-type: doc

      Install, configure, enable, update, roll back and uninstall Extensions, from the web
      console's Extensions pages, and decide which accounts may use them.

   .. grid-item-card:: Prompt engineers
      :link: ../smarter-resources/smarter-llmtool
      :link-type: doc

      Write Plugin manifests: static data, SQL, APIs, skills, web search and image search, with
      selectors that decide when each is offered.

   .. grid-item-card:: Extension developers
      :link: smarter-extensions
      :link-type: doc

      Build an Extension, using the official weather extension's ``get_weather`` tool as the
      example, test it, and publish it to the registry.
