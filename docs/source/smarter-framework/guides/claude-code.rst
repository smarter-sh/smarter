Claude Code
===========

**Claude Code** and Anthropic's Claude family of models (``claude-sonnet-4-6``,
``claude-opus-4-5``, and ``claude-haiku-4-5``) integrate with the Smarter platform to give
engineering teams—such as the **Custom Programming Area** at Northern Aurora Power & Light
(NAPL)—a governed, enterprise-ready AI pair-programming and agentic software development
environment.

Because Smarter does not bundle pre-configured Anthropic credentials out of the box, onboarding
a team involves two complementary tracks:

1. **Platform Enablement**: Connecting Smarter to Anthropic and configuring credential governance,
   cost budgets, and model catalogs.
2. **Developer Self-Onboarding**: Equipping engineers to use Claude Code from the terminal CLI,
   the Smarter Web Console Workbench, the Python SDK, or tool-augmented domain assistants.

This page organizes the contributed guides in this section into a structured **self-onboarding
learning pathway**, explains how each guide fits together, and connects you to Smarter's core
platform resources.

.. contents:: On This Page
   :depth: 2
   :local:

How Claude Code Works with Smarter
----------------------------------

Smarter supports two complementary integration patterns for Anthropic's Claude models and the
``claude`` CLI. Choose the pattern—or combination of patterns—that matches your workflow:

.. list-table::
   :header-rows: 1
   :widths: 22 39 39

   * - Aspect
     - Pattern A: Managed ``Provider`` + ``LLMClient``
     - Pattern B: Native Anthropic API ``Proxy`` Passthrough
   * - **How it works**
     - Registers Anthropic's OpenAI-compatible endpoint (``https://api.anthropic.com/v1/``) as a
       :doc:`Smarter Provider <../../smarter-resources/smarter-provider>`. Developers interact
       with Claude through a declarative :doc:`LLMClient <../../smarter-resources/smarter-llmclient>`.
     - Routes requests through Smarter's built-in ``anthropic``
       :doc:`Proxy <../../smarter-resources/smarter-proxy>` (``/api/v1/proxy/anthropic/``),
       forwarding native Anthropic Messages API calls (``v1/messages``, ``v1/models``) to
       ``https://api.anthropic.com``.
   * - **Best for**
     - ``smarter chat`` CLI sessions, the Web Console Workbench, embedded
       :doc:`Smarter Chat <../smarter-chat>` React components, and assistants that use Smarter
       :doc:`Tool Plugins, Extensions, or MCPClients <../extensibility>`.
     - Running Anthropic's native ``@anthropic-ai/claude-code`` terminal CLI (``claude``) or the
       official ``anthropic`` Python/TypeScript SDK directly against a local repository.
   * - **Authentication & Governance**
     - Upstream ``sk-ant-...`` key stored in a Smarter
       :doc:`Secret <../../smarter-resources/smarter-secret>`; developers authenticate with their
       Smarter :doc:`AuthToken <../../smarter-resources/smarter-authtoken>` or Web Console session.
     - Developers set ``ANTHROPIC_BASE_URL`` to the Smarter endpoint and authenticate with a
       Smarter ``AuthToken`` / API key. Smarter injects the upstream ``Secret`` and enforces token
       :doc:`Budget <../../smarter-resources/smarter-budget>` limits automatically.

.. tip::

   **Give Claude Code Live Context with the Smarter Project MCP Server**

   Every Smarter platform runs a read-only Streamable HTTP Model Context Protocol (MCP) server at
   ``/api/v1/mcp/smarter-project/`` that indexes Smarter repositories and Sphinx documentation.
   After installing the ``claude`` CLI, register the server so Claude Code can search Smarter
   manifests, APIs, and source code directly from your terminal:

   .. code-block:: bash

      claude mcp add --transport http smarter-project https://platform.example.com/api/v1/mcp/smarter-project/

   See :doc:`../../smarter-platform/smarter-project-mcp-server` for full details.

Choose Your Starting Point
--------------------------

Several guides in this section were contributed by different authors for the Custom Programming
Area onboarding initiative and cover overlapping ground from different perspectives (Web Console
UI vs. YAML manifests, ``smarter chat`` vs. the ``@anthropic-ai/claude-code`` npm CLI). Use the
table below to jump straight to the guide that matches your role:

.. list-table::
   :header-rows: 1
   :widths: 26 38 36

   * - Your Role & Goal
     - Recommended Starting Guide
     - Platform Reference
   * - **Platform Administrator** preferring the Web Console UI (no YAML)
     - :doc:`claude-code/adding-anthropic-provider`
     - :doc:`../../smarter-platform/adding-an-llm-provider`
   * - **Platform Administrator / DevOps** managing SAM YAML manifests in Git
     - :doc:`claude-code/getting-started-with-claude-code-2` *or*
       :doc:`claude-code/napl-adding-llm-provider`
     - :doc:`../../smarter-resources/smarter-provider`,
       :doc:`../../smarter-resources/smarter-proxy`
   * - **Custom Programming Area Developer** setting up the ``claude`` terminal CLI workstation
     - :doc:`claude-code/getting-started-with-claude-code`
     - :doc:`../developer-reference/agentic-development`
   * - **Application Developer** using ``smarter chat`` or the Web Console Workbench
     - :doc:`claude-code/claude-code-getting-started-guide` *or*
       :doc:`claude-code/getting-started-claude-code-with-smarter`
     - :doc:`../smarter-cli`, :doc:`../smarter-chat`
   * - **Full-Stack / Solo Developer** wanting a 15-minute end-to-end setup (Admin + Dev)
     - :doc:`claude-code/Getting-Started-With-Jean-Claude` *or*
       :doc:`claude-code/claude-code-with-smarter`
     - :doc:`../smarter-manifests`
   * - **Prompt / Solution Engineer** building tool-calling coding or domain assistants
     - :doc:`claude-code/tutorial` *and*
       :doc:`claude-code/napl-grid-maintenance-assistant`
     - :doc:`../extensibility`,
       :doc:`../../smarter-resources/smarter-llmtool`
   * - **Framework Engineer** extending Smarter's Python provider layer or React UI
     - :doc:`claude-code/smarter-claude-plugin`
     - :doc:`../smarter-extensions`,
       :doc:`../../smarter-platform/extensions`

Self-Onboarding Learning Pathway
--------------------------------

The 15 guides in this section are organized into four progressive modules—from initial platform
configuration to advanced framework engineering. You can follow them sequentially as a complete
self-onboarding course or select individual modules based on your responsibilities.

Module 1: Platform Setup — Adding Anthropic to Smarter (Administrator Track)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before developers can use Claude models, a Platform Administrator must register Anthropic as an
LLM provider and store the organization's Anthropic API key. All four guides in this module
achieve the same outcome through different administrative workflows:

.. list-table::
   :header-rows: 1
   :widths: 32 18 14 36

   * - Guide
     - Approach
     - Est. Time
     - Best When You Need...
   * - :doc:`claude-code/adding-anthropic-provider`
     - Web Console & Django Admin UI
     - 10 min
     - A no-YAML walkthrough for storing the credential, creating the ``anthropic`` provider,
       and registering ``claude-sonnet-4-6`` in the browser.
   * - :doc:`claude-code/getting-started-with-claude-code-2`
     - SAM CLI & YAML Manifest
     - 10 min
     - A concise CLI recipe using ``smarter manifest provider`` and ``smarter apply`` with
       a ``Secret`` reference and starter ``LLMClient`` YAML.
   * - :doc:`claude-code/napl-adding-llm-provider`
     - ``.env`` + Dual YAML Manifests
     - 15 min
     - An environment-backed setup (``SMARTER_ANTHROPIC_API_KEY``) that provisions separate
       high-reasoning (``claude-opus-4-5``) and daily coding (``claude-sonnet-4-6``) providers.
   * - :doc:`claude-code/getting-started-claude-code-as-coding-assistant`
     - Visual Guide + Video
     - 15 min
     - Step-by-step screenshots, Docker Compose restart steps, an embedded Workbench demo video,
       and a post-deployment verification checklist.

.. toctree::
   :maxdepth: 1
   :caption: Module 1: Platform Setup (Admin Track)

   claude-code/adding-anthropic-provider
   claude-code/getting-started-with-claude-code-2
   claude-code/napl-adding-llm-provider
   claude-code/getting-started-claude-code-as-coding-assistant

Module 2: Developer Onboarding — Getting Started with Claude Code (Beginner Track)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once Anthropic is available on the platform, developers can onboard their local workstations or
start coding in the Smarter Workbench. The guides below progress from zero-install browser and
``smarter chat`` workflows to full ``@anthropic-ai/claude-code`` terminal workstation configuration:

.. list-table::
   :header-rows: 1
   :widths: 32 20 14 34

   * - Guide
     - Primary Interface
     - Est. Time
     - Focus & Distinguishing Features
   * - :doc:`claude-code/claude-code-getting-started-guide`
     - ``smarter`` CLI + Workbench
     - 10 min
     - **Pure developer quickstart.** Assumes an admin already added Anthropic; covers
       ``smarter configure``, ``smarter get llmclients``, ``smarter chat``, and piping code files.
   * - :doc:`claude-code/claude-code-getting-started`
     - Conceptual + Workbench
     - 10 min
     - Introduces the relationship between ``Provider`` and ``ProviderModel``, sample JSON
       configuration, and iterative prompt patterns for code generation and debugging.
   * - :doc:`claude-code/getting-started-claude-code-with-smarter`
     - Web Console UI
     - 15 min
     - Focuses on structured prompt engineering (``Task / Context / Requirements / Output``),
       human-in-the-loop code review, and enterprise security habits.
   * - :doc:`claude-code/Getting-Started-With-Jean-Claude`
     - ``smarter`` CLI Fast-Track
     - 15 min
     - High-energy end-to-end quickstart combining ``.env`` key setup, Opus/Sonnet provider YAML,
       and your first ``smarter chat`` coding prompt.
   * - :doc:`claude-code/getting-started-with-claude-code`
     - ``claude`` npm CLI + Smarter Gateway
     - 30 min
     - **Comprehensive Custom Programming Area workstation onboarding.** Covers ``ApiKey``
       manifests, ``npm install -g @anthropic-ai/claude-code``, ``~/.claude/settings.json``
       gateway routing, a ``power_utils.py`` PoC, and an 8-part troubleshooting reference.
   * - :doc:`claude-code/claude-code-with-smarter`
     - ``smarter`` CLI + ``claude`` CLI
     - 25 min
     - **Two-part NAPL team handbook.** Part 1 covers ``Secret``, ``Provider``, and
       ``ProviderModel`` manifests; Part 2 covers developer CLI setup and deploying a personal
       ``LLMClient``.
   * - :doc:`claude-code/getting-started-claude-code-mtran`
     - ``smarter`` CLI + Sandbox UI
     - 25 min
     - Walks through scaffolding the ``NAPLClaudeCopilot`` ``LLMClient`` manifest (including nested
       ``spec.config.styles``), routing ``ANTHROPIC_BASE_URL``, and inspecting requests in the
       Web Console Sandbox.

.. toctree::
   :maxdepth: 1
   :caption: Module 2: Developer Onboarding (Beginner Track)

   claude-code/claude-code-getting-started-guide
   claude-code/claude-code-getting-started
   claude-code/getting-started-claude-code-with-smarter
   claude-code/Getting-Started-With-Jean-Claude
   claude-code/getting-started-with-claude-code
   claude-code/claude-code-with-smarter
   claude-code/getting-started-claude-code-mtran

Module 3: Applied Tutorials & Domain Assistants (Intermediate Track)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After completing basic onboarding, move on to project-based tutorials that combine Claude Code
with custom system prompts, Smarter's Python SDK, and tool calling.

.. note::

   Smarter provides three ways to equip an ``LLMClient`` with tools: declarative **Tool Plugins**
   (``spec.plugins``), installable Python **Extensions** (``spec.extensions``), and remote
   **MCP Servers** (``spec.mcpClients``). See :doc:`../extensibility` for a side-by-side
   comparison of all three mechanisms.

.. list-table::
   :header-rows: 1
   :widths: 32 22 14 32

   * - Guide
     - Key Resources Used
     - Est. Time
     - Project Outcome
   * - :doc:`claude-code/tutorial`
     - ``Secret``, ``Provider``, ``LLMClient``
     - 20 min
     - Build and iterate on a single-file HTML/Tailwind CSS Todo List web application using a
       ``web-coding-assistant`` ``LLMClient`` in the Smarter Workbench.
   * - :doc:`claude-code/napl-grid-maintenance-assistant`
     - ``ApiPlugin`` + ``LLMClient``
     - 30 min
     - Build the **NAPL Grid Maintenance Assistant**, combining ``claude-sonnet-4-6`` reasoning
       with live function calling against an internal REST API (``napl_equipment_history``).
   * - :doc:`claude-code/getting-started-claude-code`
     - ``smarter-api`` Python SDK + Plugins
     - 30 min
     - Configure an agentic ``LLMClient`` manifest and stream multi-step code generation
       programmatically via ``SmarterClient`` to build and test a ``solar_calculator.py`` module.

.. toctree::
   :maxdepth: 1
   :caption: Module 3: Applied Tutorials & Domain Assistants (Intermediate Track)

   claude-code/tutorial
   claude-code/napl-grid-maintenance-assistant
   claude-code/getting-started-claude-code

Module 4: Framework Architecture & Custom Provider Engineering (Advanced Track)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For platform and framework engineers who need to understand how Smarter translates OpenAI-formatted
chat completions into Anthropic's Messages API under the hood—or who want to build custom Python
provider adapters and embed Claude-backed chat widgets into React applications—Module 4 provides a
deep-dive architectural reference:

.. list-table::
   :header-rows: 1
   :widths: 32 22 14 32

   * - Guide
     - Audience
     - Est. Time
     - What You Will Build
   * - :doc:`claude-code/smarter-claude-plugin`
     - Smarter Core & Full-Stack Engineers
     - 45 min
     - Implement and unit-test a custom Python provider package
       (``smarter/apps/prompt/providers/claude/``), verify ``/chat/`` endpoints with ``curl``,
       and embed ``@smarter.sh/ui-chat`` in React.

.. toctree::
   :maxdepth: 1
   :caption: Module 4: Framework Architecture (Advanced Track)

   claude-code/smarter-claude-plugin

Related Documentation & Training Courses
----------------------------------------

To continue beyond these guides, explore the related references and structured training courses
across the Smarter documentation:

- **Training & Best Practices**:

  - :doc:`../../smarter-instructors/example-courses/micro-courses/agentic-development` — Instructor
    and self-study curriculum (8-hour bootcamp, 2-week, and 4-week plans) for agentic coding with
    Claude Code, ``CLAUDE.md`` project memory, TDD loops, and subagent workflows.
  - :doc:`../developer-reference/agentic-development` — Reference guide on context management,
    verification gates, and how Smarter's own codebase is built with Claude Code.

- **Platform Administration & Resources**:

  - :doc:`../../smarter-platform/adding-an-llm-provider` — Canonical platform administration guide
    for registering OpenAI-compatible providers and syncing model catalogs.
  - :doc:`../../smarter-resources/smarter-provider` — YAML specification for ``kind: Provider``.
  - :doc:`../../smarter-resources/smarter-proxy` — YAML specification for ``kind: Proxy``,
    including the built-in ``anthropic`` passthrough proxy (``/api/v1/proxy/anthropic/``).
  - :doc:`../../smarter-platform/smarter-project-mcp-server` — Connecting Claude Code to Smarter's
    hosted MCP server for live repository and documentation search.

- **Tools, Extensions & Chat UI**:

  - :doc:`../extensibility` — How declarative Tool Plugins, Python Extensions, and MCP Servers
    compare and work together on an ``LLMClient``.
  - :doc:`../smarter-extensions` — Authoring and packaging Python tool Extensions for the Smarter
    Extension registry.
  - :doc:`../smarter-chat` — Hosting and embedding the Smarter Chat React web application.
  - :doc:`../../external-links/claude-reference` — External links to official Anthropic and Claude
    Code documentation.

