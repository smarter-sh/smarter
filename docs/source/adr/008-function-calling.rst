ADR-008: Function Calling
=========================

Status
------
Accepted

Context
-------
An LLM knows only what it was trained on. Function calling, which every OpenAI-compatible api
supports, lets it ask the application to run a tool and answer from the result. Smarter's core
mission is no-code abstractions, through manifests, the CLI and the broker model
(:doc:`ADR-005 <005-manifests>`, :doc:`ADR-024 <024-broker-model>`), but some tools can only be
written as code.

Smarter first gave LLMs tools in two ways: Plugins, SAM manifests that configure one of the
``smarter.apps.llmtool`` app's built-in tool patterns, and three Python functions
(``get_current_weather``, ``calculator`` and ``date_calculator``) hardcoded into the chat provider.
Adding a Python tool meant changing Smarter itself: a new choice in an enum, new branches in the
chat provider, and a release.

Decision
--------
An LLMClient's tools come from three sources, each listed in its manifest, and all offered to the
LLM through the same tool call loop in the OpenAI-compatible chat provider:

1. **Plugins are configuration.** A prompt engineer configures one of Smarter's built-in tool
   patterns (static data, SQL, REST APIs, skills, web search, image search) in a SAM manifest,
   owned by an account and listed in ``spec.plugins``. A Plugin is offered when a prompt matches
   its selector. ``smarter.apps.llmtool.plugin``.
2. **Extensions are code.** A Python developer writes a package whose tools are classes with a
   Pydantic arguments model, which is their JSON Schema, and publishes it to the signed Smarter
   Extension registry. A platform superuser installs it at run time, without a redeploy, and
   LLMClients list it in ``spec.extensions``. ``smarter.apps.llmtool.extension``.
3. **MCP servers** offer the tools of services that already speak the Model Context Protocol,
   through MCPClients listed in ``spec.mcpClients``. ``smarter.apps.mcpclient``.

Smarter has no built-in functions. Its own Python tools are official Extensions, in their own
repositories.

Alternatives Considered
-----------------------
- Implementing function calling without a plugin-based architecture.
- Built-in functions in the chat provider, extended by changing Smarter's code. This was Smarter's
  first design, replaced by Extensions.
- Extensions only, without Plugins. Every tool would need a Python developer and a superuser,
  which defeats the no-code approach.
- MCP servers only. They need a server to run and host, and can't use the platform's own code,
  Secrets and models.

Consequences
------------
- **Positive:**

  - Prompt engineers add common tools in minutes, with no code and no deployment.
  - Developers add any tool that Python can implement, and administrators install, update and
    roll it back at run time.
  - Every tool's definition is generated from the model that validates its arguments, so the two
    can't disagree.
  - Tool errors are returned to the LLM, which can recover, rather than failing the prompt.

- **Negative:**

  - Contributors must understand which of the three sources suits a tool.
  - Extensions run unsandboxed, with the platform's own access, so administrators must trust their
    publishers.
  - Tools are offered differently: a Plugin only when a prompt matches its search terms, an
    Extension's and an MCP server's tools on every prompt of an LLMClient that lists them.

Related ADRs
------------
- :doc:`ADR-000: Introduction <000-intro>`
- :doc:`ADR-005: Manifests <005-manifests>`
- :doc:`ADR-024: Broker Model <024-broker-model>`
- :doc:`ADR-031: Pydantic Models Over Raw JSON <031-pydantic-over-json>`
