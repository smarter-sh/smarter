.. _napl-getting-started-claude-code:

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

This tutorial assumes you already have:

- An **active Smarter account**. Your administrator has already provisioned
  your credentials — you know how to log in.
- Comfort working in a **terminal** (bash, zsh, or PowerShell).
- A **code editor** installed (VS Code, JetBrains, or similar).
- Basic familiarity with **YAML** syntax (indentation, key-value pairs).

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

The flow is simple: your administrator sets up **providers**, you create
**chatbots** that reference those providers, and you interact with chatbots
through the CLI or the web console.

Step-by-Step: Your First Claude Code Session
=============================================

Step 4: Discover Available Chatbots
-------------------------------------

.. code-block:: bash

   smarter get chatbots

This lists every chatbot assigned to your account. Note the name of a
chatbot configured with the Anthropic provider (e.g. ``anthropic-opus``
or ``claude-code-assistant``).

To see which provider and model a chatbot uses:

.. code-block:: bash

   smarter describe chatbot <chatbot-name>

Step 5: Chat from the Terminal
--------------------------------

.. code-block:: bash

   smarter chat <chatbot-name>

This opens an interactive session with streaming responses. Type a prompt
and press Enter. For example:

.. code-block:: text

   Write a Python function that validates an email address using regex.

Claude will respond with a complete implementation. Type ``exit`` or press
``Ctrl+C`` to end the session.

Step 6: Chat from the Workbench
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

Step 7: Pipe Code to Claude from Your Terminal
-------------------------------------------------

You can send source files directly to Claude for review, refactoring
suggestions, or bug analysis:

.. code-block:: bash

   cat my_script.py | smarter chat <chatbot-name> --prompt "Review this code for bugs and suggest improvements"

Or ask Claude to explain unfamiliar code:

.. code-block:: bash

   cat legacy_module.py | smarter chat <chatbot-name> --prompt "Explain what this code does, section by section"

Step 8: Create Your Own Custom Chatbot (Optional)
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

Run this sequence end to end to confirm your setup is complete:

.. code-block:: bash

   # 1. Verify platform connectivity
   smarter status

   # 2. Confirm Anthropic provider is active
   smarter get providers

   # 3. List your chatbots
   smarter get chatbots

   # 4. Start an interactive session
   smarter chat <chatbot-name>

In the chat session, type:

.. code-block:: text

   Explain the difference between a Python list and a tuple in two sentences.

Expected response (approximate):

.. code-block:: text

   A Python list is a mutable, ordered collection that can be changed after
   creation, while a tuple is immutable and cannot be modified once defined.
   Tuples are generally faster and used for fixed data, whereas lists are
   preferred when the collection needs to change.

A clear, accurate response within a few seconds confirms that:

- Your CLI is authenticated and connected.
- The Anthropic provider is active and verified.
- Claude is processing requests through Smarter.

You are ready to use Claude Code as your virtual CoPilot.

Troubleshooting
===============

**"Not authenticated" or "Invalid API key"**
   Run ``smarter configure`` and re-enter your API key. You can also pass it
   inline with ``--api_key`` for a single command.

**"No chatbots found"**
   Your administrator has not yet assigned a chatbot to your account, or you
   have not created one yourself. Ask your administrator for access, or
   create your own chatbot using the manifest in Step 8.

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

**YAML errors when creating a chatbot manifest**
   YAML requires spaces (not tabs) for indentation. Use 2-space indentation
   consistently. Run ``smarter manifest chatbot`` to see a valid template.

.. seealso::

   - :doc:`/smarter-framework/smarter-cli` — CLI installation and reference
   - :doc:`/smarter-platform/api-keys` — Managing your API keys
   - :doc:`/smarter-platform/adding-an-llm-provider` — How providers are configured
   - :doc:`/smarter-resources/smarter-provider` — Provider technical reference
   - `Anthropic Claude Documentation <https://docs.anthropic.com/>`_
