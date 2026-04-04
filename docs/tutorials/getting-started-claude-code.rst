Getting Started with Claude Code in Smarter
===========================================

.. meta::
   :description: Self-onboarding tutorial for NAPL programmers to configure and use Anthropic’s Claude Code agentic coding system through the Smarter on-premise LLM platform.

Overview
--------

This tutorial guides you—highly technical programmers at Northern Aurora Power & Light (NAPL)—through configuring **Claude Code** (Anthropic’s agentic coding assistant) inside **Smarter**, our company-wide on-premise LLM authoring and hosting platform.

Smarter abstracts every LLM provider behind a unified YAML-first interface. Although Smarter ships with native support for several providers (OpenAI, Google, Meta, DeepSeek, etc.), **Claude Code** is not enabled out-of-the-box. You will add it yourself by declaring an Anthropic-backed provider in a declarative manifest, then use it for real-world coding tasks.

Goal
----

We will use Claude Code with Smarter to **autonomously read your codebase, propose multi-file changes, run tests, commit code, and iterate until the feature or bug-fix is complete**—all while staying inside the NAPL-approved, on-premise, cost-tracked environment.

Prerequisites
-------------

You are assumed to already have:

* A valid Smarter account and the ability to log in to the Smarter dashboard (``https://smarter.napl.internal``).
* Familiarity with YAML and declarative configuration (Kubernetes-style manifests).
* Basic familiarity with the Smarter CLI (``smarter`` command) or the Prompt Engineer Workbench.
* Access to your NAPL Anthropic API key (provisioned by the Security team and stored as a Smarter secret; you will reference it by name).
* A local clone of the project repository you want to work on.
* Python 3.11+ and Git installed (for the proof-of-concept example).

If any of the above are missing, contact your team’s Smarter administrator before proceeding.

Setup
-----

1. **Install the Smarter CLI** (one-time, if not already present in your IDE environment):

   .. code-block:: bash

      pip install smarter-cli

2. **Authenticate the CLI** (uses your Smarter SSO):

   .. code-block:: bash

      smarter login

3. **Verify you can see the company-provided Anthropic secret**:

   .. code-block:: bash

      smarter secrets list | grep anthropic

   You should see a secret named something like ``napl-anthropic-claude-key``.

Concept Overview
----------------

Smarter is built around **declarative manifests**—plain YAML files that describe AI resources (Chatbots, Agents, Tools, etc.). Key concepts you need for Claude Code:

* **Provider** — The upstream LLM service (``anthropic`` in our case).
* **Model** — The specific Claude variant that powers Claude Code (``claude-3-5-sonnet-20241022`` or newer).
* **Resource** — A versioned, namespaced object (e.g., ``ClaudeCodeAgent``) that you ``smarter apply``.
* **Plugins** — Declarative YAML tools that give the LLM the ability to read/write files, run shell commands, execute tests, and commit code—exactly what makes Claude Code “agentic.”
* **Secret references** — Smarter never exposes raw API keys; you reference company-managed secrets.
* **Unified API** — Once the resource exists, you call it via the Smarter Python SDK, REST API, or IDE integration exactly as you would any other model.

Adding Claude Code is therefore just a matter of writing (or copying) the right manifest and applying it.

Step-by-Step
------------

1. **Create a new manifest file**

   In the root of your project (or in a ``.smarter/`` directory), create ``claude-code-agent.yaml``:

   .. code-block:: yaml
      :caption: claude-code-agent.yaml

      apiVersion: smarter.napl.internal/v1
      kind: Agent
      metadata:
        name: claude-code-prod
        namespace: your-team-namespace
        labels:
          purpose: coding-assistant
      spec:
        config:
          provider: anthropic
          defaultModel: claude-3-5-sonnet-20241022
          apiKeySecretRef: napl-anthropic-claude-key   # company secret
          temperature: 0.2
          maxTokens: 8192
        systemRole: |
          You are Claude Code, an agentic coding assistant inside NAPL’s Smarter platform.
          You have full read/write access to the current Git repository.
          Always use the available plugins to explore, edit, test, and commit code.
          Think step-by-step and explain your plan before acting.
        plugins:
          - name: filesystem
            type: built-in
            config:
              root: "."
          - name: shell
            type: built-in
            config:
              allowedCommands: ["git", "pytest", "ruff", "npm", "make"]
          - name: git-commit
            type: custom
            config:
              description: "Commit changes with a conventional commit message"

2. **Apply the manifest**

   .. code-block:: bash

      smarter apply -f claude-code-agent.yaml

   You should see output confirming the resource was created or updated.

3. **Verify the resource**

   .. code-block:: bash

      smarter get agent claude-code-prod

4. **Test in the Prompt Engineer Workbench** (optional but recommended)

   * Log into the Smarter web UI → **Workbench**.
   * Select your new agent ``claude-code-prod``.
   * Type a simple request: “Add a new endpoint to return current power grid status.”

5. **Integrate into your workflow** (via SDK example)

   Install the Python SDK if needed:

   .. code-block:: bash

      pip install smarter-api

   Then:

   .. code-block:: python

      from smarter import SmarterClient
      client = SmarterClient()
      response = client.chat.completions.create(
          agent="claude-code-prod",
          messages=[{"role": "user", "content": "Refactor the billing module to use async database calls"}],
          stream=True
      )
      for chunk in response:
          print(chunk.delta.content, end="")

Proof of Concept
----------------

After completing the steps above, run this command in your project root:

.. code-block:: bash

   smarter chat claude-code-prod --prompt "Implement a new Python module that calculates expected power output from a solar array given irradiance and panel efficiency. Include unit tests and a conventional commit."

Expected result: Claude Code will:

* Explore your repo using the filesystem plugin.
* Create a new file ``solar_calculator.py``.
* Write comprehensive tests.
* Run ``pytest`` via the shell plugin.
* Commit the changes with a proper Git message.

You will see the full agentic trace in your terminal (or the Workbench) and the files will appear in your working directory. This is the concrete outcome you should achieve before considering yourself onboarded.

Troubleshooting
---------------

**“Provider ‘anthropic’ is not recognized”**

   Your Smarter instance may still be on an older build. Run ``smarter version`` and ensure you are on v0.13+ (or whatever version the infrastructure team has deployed). If needed, ask the Smarter admins to enable the Anthropic backend module.

**“Secret napl-anthropic-claude-key not found”**

   Verify the secret exists with ``smarter secrets list``. If missing, open a ticket with the Security team referencing “NAPL Anthropic enterprise key for Smarter”.

**Agent times out or returns empty**

   Increase ``maxTokens`` or lower ``temperature`` in the manifest and re-apply. Also check token consumption in the Smarter dashboard under **Usage → your-namespace**.

**Plugins fail with permission errors**

   The ``shell`` plugin only allows whitelisted commands. Add any new tools you need to the ``allowedCommands`` list and re-apply the manifest.

**Changes not appearing in Git**

   Make sure you are running the command from inside a Git repository and that the ``git-commit`` plugin is enabled.

**Rate-limit or cost spikes**

   All usage is tracked by the accounting codes configured by the Finance team. Use the dashboard filter ``provider=anthropic`` to monitor.

You are now fully onboarded and ready to use Claude Code inside Smarter for all your custom programming work at NAPL.

Questions or feature requests? Open an issue in the internal Smarter repository or reach out to the IT Generative AI team.