Extensibility
=============

An LLM knows only what it was trained on. Tools are how Smarter gives it everything else: today's
weather, a customer's order, a row in your database, a calculation it would otherwise guess at.
When a prompt arrives, Smarter offers the LLM the tools that its LLMClient lists, the LLM asks
to call one, Smarter runs it and returns the result, and the LLM writes its answer from that
result. See :doc:`../smarter-resources/llmtool/how-tools-work` for how this works with any
OpenAI-compatible API.

Smarter has two ways to add tools, because there are two kinds of people who add them.

**Plugins** are configuration. A prompt engineer writes a YAML manifest that configures one of
Smarter's built-in tool patterns: answer from static data, run a SQL query, call a REST API,
follow a skill, search the web, or search for images. Plugins are
:doc:`SAM resources <smarter-manifests>`, applied with the ``smarter`` CLI or the API, owned by
an account, and shared like any other resource. No code is written or installed.

**Extensions** are code. A Python developer writes a package whose tools do whatever Python can
do, packages it as a zip archive, and publishes it to the Smarter Extension registry. A platform
administrator installs it at run time, from the Django admin console, much as a WordPress
administrator installs a plugin. Every LLMClient on the platform can then list it.

Plugins and Extensions Compared
-------------------------------

.. list-table::
   :header-rows: 1
   :widths: 22 39 39

   * -
     - Plugins
     - Extensions
   * - What it is
     - A SAM manifest that configures a built-in tool pattern
     - A Python package with its own tools, settings, documentation and lifecycle
   * - Written by
     - Prompt engineers, in YAML
     - Python developers
   * - Installed by
     - Any user, with ``smarter apply``
     - A platform superuser, from the admin console or the registry
   * - Scope
     - Owned by a user, shared within an account
     - Platform-wide, available to every account or to listed accounts
   * - Can do
     - What its pattern does: static data, SQL, REST APIs, skills, web and image search
     - Anything Python can do, with the platform's code and libraries
   * - Configuration
     - In its manifest, with credentials in Secrets and Connections
     - Settings that the administrator configures, with credentials in Secrets
   * - Selection
     - Offered when a prompt matches its selector's search terms
     - Offered on every prompt of an LLMClient that lists it
   * - Listed in an LLMClient's
     - ``spec.plugins``
     - ``spec.extensions``
   * - Lives in
     - ``smarter.apps.llmtool.plugin``
     - ``smarter.apps.llmtool.extension``
   * - Distribution
     - Manifests, in source control or the API
     - Zip archives, from the signed Smarter Extension registry or uploaded
   * - Trust
     - Runs inside Smarter's own, reviewed tool patterns
     - Runs arbitrary code with full access to the platform: install only what you trust

Choose a Plugin when one of the built-in patterns does the job: it takes minutes, needs no
deployment, and anyone in an account can manage it. Choose an Extension when it doesn't, for
example to geocode an address and query a weather service, to compute rather than look up, or
to integrate a service whose API needs more than a REST call.

Both kinds of tool appear side by side in an LLMClient's manifest:

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

MCP servers are a third source of tools, for services that already speak the Model Context
Protocol. See :doc:`../smarter-resources/smarter-mcpclient`.

Where to Go Next
----------------

.. grid:: 1 1 3 3
   :gutter: 2

   .. grid-item-card:: Administrators
      :link: ../smarter-platform/extensions
      :link-type: doc

      Install, configure, enable, update, roll back and uninstall Extensions, from the admin
      console or the registry, and decide which accounts may use them.

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
