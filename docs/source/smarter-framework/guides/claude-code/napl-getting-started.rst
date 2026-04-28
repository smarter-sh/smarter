.. _getting-started-with-claude-code-napl:

================================================================
Getting Started: Using Claude Code with Smarter for Programmers
================================================================

.. contents:: Table of Contents
   :local:
   :depth: 2

Goal
====

We will use Claude Code with Smarter to set up a virtual CoPilot coding pair,
send your first prompt from both the terminal and the browser, and integrate
Claude Code into your daily development workflow — all without managing any
API keys yourself.

By the end of this tutorial you will be able to chat with Claude through the
Smarter CLI, use the Prompt Engineer Workbench for rapid prototyping, and
pipe source code to Claude for review directly from your terminal.

Prerequisites
=============

You are a working programmer at Northern Aurora Power & Light (NAPL). You
already have a Smarter account and know how to log in. You are also expected
to be comfortable with:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Topic
     - What you need to know
   * - Terminal
     - Comfortable with a Unix/macOS terminal or Windows PowerShell;
       able to set environment variables and edit configuration files.
   * - YAML
     - Able to read and write basic YAML — indentation, key-value pairs.
   * - Node.js / npm
     - Able to install a global npm package (``npm install -g``).
   * - Code editor
     - VS Code, JetBrains, or similar installed.
   * - Smarter account
     - You have been provisioned a Smarter account and can log in to
       the web console.

Verify your Node.js version before proceeding:

.. code-block:: bash

   node --version
   # Expected: v18.x.x or higher

.. note::

   You do **not** need your own Anthropic API key. Smarter manages provider
   credentials centrally. Your administrator has already configured Anthropic
   as an LLM provider and created chatbots backed by Claude models.

Setup
=====

Step 1: Install the Smarter CLI
---------------------------------

Follow the installation instructions in :doc:`/smarter-framework/smarter-cli`
to download the CLI binary for your operating system and add it to your
``PATH``.

Confirm it is working:

.. code-block:: bash

   smarter version

You should see a version string of **0.11.0 or later**.

Step 2: Create Your Smarter API Key
--------------------------------------

Your Smarter API key is your personal identity on the platform. Every request
you make is authenticated and tracked through this key.

1. Log in to the **Smarter web console**.
2. Click your profile icon (top-right) and select **API Keys**.
3. Click **Create API Key**, give it a descriptive name (e.g.
   ``shivani-dev-key``), and copy the value immediately.

Set the key as an environment variable so you do not have to type it
repeatedly:

.. code-block:: bash

   export SMARTER_API_KEY=your-api-key-here

.. tip::

   Add the ``export`` line to your shell profile (``~/.bashrc``,
   ``~/.zshrc``, or equivalent) so it persists across terminal sessions.

Step 3: Configure the CLI
----------------------------

.. code-block:: bash

   smarter configure

When prompted, provide:

- **Target environment** — ask your administrator for the correct value
  (e.g. ``prod``, ``alpha``).
- **API key** — the key you created in Step 2.

Verify the connection:

.. code-block:: bash

   smarter status

A successful response confirms the platform is reachable and your
credentials are valid.

Step 4: Install Claude Code
-----------------------------

Claude Code is distributed as a global npm package:

.. code-block:: bash

   npm install -g @anthropic-ai/claude-code

Verify the installation:

.. code-block:: bash

   claude --version

Step 5: Configure Claude Code to Use the Smarter Gateway
----------------------------------------------------------

Claude Code must be redirected from Anthropic's public API to the Smarter
gateway. Create or edit ``~/.claude/settings.json``:

.. code-block:: json

   {
     "env": {
       "ANTHROPIC_BASE_URL": "https://smarter.internal",
       "ANTHROPIC_AUTH_TOKEN": "<YOUR_SMARTER_API_KEY>"
     }
   }

Replace ``<YOUR_SMARTER_API_KEY>`` with the key you created in Step 2.

.. important::

   ``ANTHROPIC_AUTH_TOKEN`` here is your **Smarter API key** — not an
   Anthropic key. Smarter exposes an Anthropic-compatible API surface;
   Claude Code sends your Smarter token as its bearer credential, and the
   gateway uses its own centrally managed Anthropic key upstream. You never
   possess or manage an Anthropic credential.

Step 6: Pre-accept the Claude Code Onboarding
------------------------------------------------

When Claude Code detects a custom ``ANTHROPIC_BASE_URL`` it may stall on
the first-run wizard. Pre-mark onboarding as complete by creating or
editing ``~/.claude.json``:

.. code-block:: json

   {
     "hasCompletedOnboarding": true
   }

Concept Overview
================

Before diving into usage, here are the three core concepts you will interact
with daily:

**Provider**
   A configured LLM backend. Your administrator has registered Anthropic as
   a provider, making Claude models available across the platform. You do not
   manage providers — you consume them.

**Chatbot**
   A named resource that bundles a provider, a specific model, a system
   prompt, and optional plugins. Chatbots are what you interact with.
   Think of a chatbot as a pre-configured coding assistant with a specific
   personality and set of capabilities.

**Manifest**
   A declarative YAML file (called a **SAM** manifest) that defines any
   Smarter resource. Providers, chatbots, and plugins are all described
   this way. You will author chatbot manifests to customize your own
   coding assistants.

The Smarter Gateway
~~~~~~~~~~~~~~~~~~~~

Smarter acts as a managed proxy between developer tools and upstream LLM
providers. Every prompt flows through the gateway:

.. code-block:: text

   Developer Workstation
       |
       |  claude (Claude Code CLI)
       |  ANTHROPIC_BASE_URL  -> https://smarter.internal
       |  ANTHROPIC_AUTH_TOKEN -> <your Smarter API key>
       v
   Smarter Gateway (on-premise)
       |  1. Authenticates your Smarter API key
       |  2. Assigns cost-accounting code
       |  3. Writes audit log entry
       |  4. Substitutes platform-level Anthropic key
       |  5. Forwards request to Anthropic
       v
   Anthropic API (api.anthropic.com)
       |  Claude processes the request
       v
   Response flows back the same path

Common CLI Commands
~~~~~~~~~~~~~~~~~~~~

You interact with Smarter resources through the CLI:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Command
     - What it does
   * - ``smarter apply -f <file.yml>``
     - Creates or updates a resource
   * - ``smarter get <kind>``
     - Lists resources of a given kind
   * - ``smarter describe <kind> <name>``
     - Returns the live manifest including status
   * - ``smarter delete <kind> <name>``
     - Removes a resource
   * - ``smarter manifest <kind> -o yaml``
     - Prints an example manifest template

The flow is simple: your administrator sets up **providers**, you create
**chatbots** that reference those providers, and you interact with chatbots
through the CLI, the web console, or Claude Code.

Step-by-Step: Your First Claude Code Session
=============================================

Step 7: Discover Available Chatbots
-------------------------------------

.. code-block:: bash

   smarter get chatbots

This lists every chatbot assigned to your account. Note the name of a
chatbot configured with the Anthropic provider (e.g. ``anthropic-opus``
or ``claude-code-assistant``).

To see which provider and model a chatbot uses:

.. code-block:: bash

   smarter describe chatbot <chatbot-name>

Step 8: Chat from the Terminal
--------------------------------

.. code-block:: bash

   smarter chat <chatbot-name>

This opens an interactive session with streaming responses. Type a prompt
and press Enter. For example:

.. code-block:: text

   Write a Python function that validates an email address using regex.

Claude will respond with a complete implementation. Type ``exit`` or press
``Ctrl+C`` to end the session.

Step 9: Chat from the Workbench
----------------------------------

The Prompt Engineer Workbench is a browser-based interface for interacting
with chatbots. It is especially useful for iterating on prompts and tuning
parameters.

1. Open the **Smarter web console** in your browser.
2. Navigate to **Workbench** in the left sidebar.
3. Select your Claude-backed chatbot from the dropdown.
4. Type a prompt and press Enter.

The Workbench lets you adjust **temperature**, **max tokens**, and the
**system prompt** in real time — useful for experimenting before you commit
to a configuration.

Step 10: Pipe Code to Claude from Your Terminal
-------------------------------------------------

You can send source files directly to Claude for review, refactoring
suggestions, or bug analysis:

.. code-block:: bash

   cat my_script.py | smarter chat <chatbot-name> --prompt "Review this code for bugs and suggest improvements"

Or ask Claude to explain unfamiliar code:

.. code-block:: bash

   cat legacy_module.py | smarter chat <chatbot-name> --prompt "Explain what this code does, section by section"

Step 11: Create Your Own Custom Chatbot (Optional)
---------------------------------------------------

Power users can define their own chatbot with a tailored system prompt.
Create a file named ``my-copilot.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Chatbot
   metadata:
     name: my-copilot
     description: Personal coding assistant for Python development
     version: 1.0.0
   spec:
     config:
       provider: anthropic
       defaultModel: claude-sonnet-4-6
       defaultSystemRole: |
         You are an expert Python developer. Write clean, well-documented
         code that follows PEP 8 conventions. When reviewing code, focus
         on correctness, readability, and performance.
       temperature: 0.2
       maxTokens: 8192
     plugins: []

Apply and start using it:

.. code-block:: bash

   smarter apply -f my-copilot.yaml
   smarter chat my-copilot

.. note::

   The ``provider`` field must reference a provider that your administrator
   has already registered. Use ``smarter get providers`` to see what is
   available.

Proof of Concept
================

Create a file called ``power_utils.py`` with the following NAPL-relevant code:

.. code-block:: python

   import math

   def calculate_reactive_power(apparent_power_kva: float,
                                 power_factor: float) -> float:
       """Calculate reactive power (kVAR) from apparent power and power factor.

       Uses the AC power triangle: Q = S * sin(arccos(PF))
       """
       if apparent_power_kva <= 0:
           raise ValueError(f"apparent_power_kva must be > 0; got {apparent_power_kva}")
       if not 0.0 <= power_factor <= 1.0:
           raise ValueError(f"power_factor must be in [0, 1]; got {power_factor}")
       return apparent_power_kva * math.sin(math.acos(power_factor))

Navigate to the directory containing the file and start Claude Code:

.. code-block:: bash

   cd /path/to/power_utils.py
   claude

At the prompt, type:

.. code-block:: text

   Explain the calculate_reactive_power function, including the math
   and a worked example with 100 kVA at 0.85 power factor.

**Expected result**: Claude responds with a clear explanation of the AC
power triangle, the relationship Q = S * sin(arccos(PF)), and a worked
example showing approximately 52.68 kVAR.

You can also verify the full pipeline from the CLI:

.. code-block:: bash

   # 1. Verify platform connectivity
   smarter status

   # 2. Confirm Anthropic provider is active
   smarter get providers

   # 3. Confirm Claude Code is pointing at Smarter
   claude
   /status
   # Endpoint must show https://smarter.internal

If Claude returns a substantive analysis of the power utility code, your
setup is working end-to-end:

- Claude Code is routing through the Smarter gateway.
- The gateway is authenticating your Smarter API key.
- The gateway is forwarding to Anthropic using the platform credential.
- The response is returned through the same path.

**You are fully onboarded.**

Troubleshooting
===============

**"Not authenticated" or "Invalid API key"**
   Run ``smarter configure`` and re-enter your API key. You can also pass it
   inline with ``--api_key`` for a single command.

**"No chatbots found"**
   Your administrator has not yet assigned a chatbot to your account, or you
   have not created one yourself. Ask your administrator for access, or
   create your own chatbot using the manifest in Step 11.

**Slow or timed-out responses**
   Run ``smarter status`` to check platform health. If the platform is
   healthy, the delay is likely on Anthropic's side. Wait a moment and
   retry. Larger prompts (e.g. piping entire files) take longer to process.

**"Provider not available"**
   The Anthropic provider may have failed verification. Run
   ``smarter describe provider anthropic-opus`` and check the ``status``
   section. If verification has failed, contact your administrator.

**Unexpected or low-quality responses**
   Run ``smarter describe chatbot <chatbot-name>`` to confirm which model
   the chatbot uses. Different Claude models have different capabilities:

   - **Claude Opus** — best for complex reasoning and large codebases.
   - **Claude Sonnet** — faster and more cost-efficient for routine tasks.

   Also check the ``temperature`` setting. Values above 0.5 increase
   creativity but reduce consistency.

**Claude Code shows ``api.anthropic.com`` in ``/status``**
   The ``~/.claude/settings.json`` file was not saved correctly, or the
   terminal session predates its creation. Validate the JSON:

   .. code-block:: bash

      python3 -m json.tool ~/.claude/settings.json

   Close all terminals and open a fresh one before running ``claude``.

**Claude Code returns a 401 error**
   The ``ANTHROPIC_AUTH_TOKEN`` does not match an active Smarter API key.
   Run ``smarter get apikeys`` to confirm the key exists, then check
   ``~/.claude/settings.json`` for extra whitespace around the token value.

**Claude Code returns a 403 or "Model not available" error**
   The requested model is not configured at the platform level, or your
   account does not have access to it. Use ``/model`` inside Claude Code to
   check the active model. Contact NAPL IT to request access.

**YAML errors when creating a chatbot manifest**
   YAML requires spaces (not tabs) for indentation. Use 2-space indentation
   consistently. Run ``smarter manifest chatbot`` to see a valid template.

.. seealso::

   - :doc:`/smarter-framework/smarter-cli` — CLI installation and reference
   - :doc:`/smarter-platform/api-keys` — Managing your API keys
   - :doc:`/smarter-platform/adding-an-llm-provider` — How providers are configured
   - :doc:`/smarter-resources/smarter-provider` — Provider technical reference
   - `Anthropic Claude Documentation <https://docs.anthropic.com/>`_
   - `Claude Code Overview <https://docs.anthropic.com/en/docs/claude-code/overview>`_
