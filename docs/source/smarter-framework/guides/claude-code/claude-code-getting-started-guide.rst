.. _getting-started-claude-code:

=============================================
Getting Started with Claude Code on Smarter
=============================================

.. contents:: Table of Contents
   :local:
   :depth: 2

Goal
====

Get your first **Claude Code** response through **Smarter** — from both the
terminal and the browser — and integrate it into your daily development
workflow.

Prerequisites
=============

- An active Smarter account. If you don't have one, contact your administrator.
- Comfort working in a terminal and with command-line tools.
- A code editor (VS Code recommended).

.. note::

   Your administrator has already configured Anthropic as an LLM provider.
   You do not need your own Anthropic API key — Smarter manages provider
   credentials centrally.

Setup
=====

Step 1: Install the Smarter CLI
---------------------------------

Follow the installation instructions in :doc:`/smarter-framework/smarter-cli`
to download the binary for your operating system and add it to your ``PATH``.

Confirm the installation:

.. code-block:: bash

   smarter version

Step 2: Create a Smarter API Key
----------------------------------

Your Smarter API key is your identity on the platform. You need it before
you can configure the CLI.

1. Log in to the Smarter web console.
2. Click your profile icon (top-right) and select **API Keys**.
3. Click **Create API Key**, give it a name (e.g. ``my-cli-key``), and copy
   the value.

Set it as an environment variable so you don't have to type it repeatedly:

.. code-block:: bash

   export SMARTER_API_KEY=your-api-key-here

Step 3: Configure the CLI
----------------------------

.. code-block:: bash

   smarter configure

When prompted, provide the target environment (e.g. ``prod``, ``alpha``) and
your API key from Step 2.

Concept Overview
================

Your Smarter API key authenticates every request you make. When you send a
prompt, Smarter routes it to the correct provider backend — in this case,
Anthropic — handles authentication on your behalf, and returns the response.
You never touch Anthropic credentials directly.

Three concepts you need to understand:

- **Provider** — a configured LLM backend (Anthropic, OpenAI, etc.). Your
  administrator manages these.
- **Chatbot** — a named resource that bundles a provider, a model, a system
  prompt, and optional data plugins. This is what you interact with.
- **Manifest** — the YAML file that defines any Smarter resource. Every
  chatbot, provider, and plugin is described this way.

You interact with **chatbots**, not providers directly. Your administrator has
already created a chatbot backed by Claude Code — you just need its name.

Step-by-Step: Using Claude Code
================================

Step 4: Find Your Chatbot
---------------------------

.. code-block:: bash

   smarter get chatbots

This lists every chatbot assigned to your account. Note the name of a chatbot
configured with the Anthropic provider.

Step 5: Chat from the Terminal
--------------------------------

.. code-block:: bash

   smarter chat <chatbot-name>

This opens an interactive session with streaming responses. Type your prompt
and press Enter.

Useful commands while exploring:

.. code-block:: bash

   # Confirm the Anthropic provider is active
   smarter describe provider anthropic

   # Inspect a chatbot's full configuration
   smarter describe chatbot <chatbot-name>

Step 6: Chat from the Browser
--------------------------------

1. Navigate to **Workbench** in the left sidebar of the Smarter web console.
2. Select your Claude Code chatbot.
3. Type a prompt and press Enter.

The Workbench lets you tune system prompts, temperature, and max tokens —
useful for testing before you automate or deploy.

Step 7: Integrate into Your Workflow
--------------------------------------

**Terminal** — pipe code directly to the CLI:

.. code-block:: bash

   cat my_script.py | smarter chat <chatbot-name> --prompt "Review this code for bugs"

**REST API** — call Smarter from scripts or CI/CD pipelines. See the
:doc:`/external-links/swagger` for endpoint details.

**VS Code** — install the
`Smarter YAML extension <https://marketplace.visualstudio.com/items?itemName=querium.smarter-manifest>`_
for manifest authoring with autocomplete and validation.

Proof of Concept
================

Run this sequence end to end:

.. code-block:: bash

   smarter status                    # platform is reachable
   smarter get providers             # anthropic is listed and active
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

A clear, concise response within a few seconds means your setup is complete.

Troubleshooting
===============

**"Not authenticated"**
   Run ``smarter configure`` and re-enter your API key. You can also pass it
   inline with ``--api_key``.

**"No chatbots found"**
   Your administrator has not yet assigned a chatbot to your account. Ask them
   to grant you access to a chatbot configured with the Anthropic provider.

**Slow or timed-out responses**
   Run ``smarter status``. If the platform is healthy, the delay is on
   Anthropic's side — wait a minute and retry.

**"Provider not available"**
   The Anthropic provider failed verification. Run
   ``smarter describe provider anthropic`` and check the ``status`` section,
   then contact your administrator.

**Unexpected model behavior**
   Run ``smarter describe chatbot <chatbot-name>`` to confirm which model the
   chatbot is using. Different Claude models have different capabilities and
   context window sizes.

.. seealso::

   - :doc:`/smarter-framework/smarter-cli`
   - :doc:`/smarter-platform/api-keys`
   - :doc:`/smarter-resources/smarter-provider`
   - :doc:`/smarter-platform/adding-an-llm-provider`
   - :doc:`/external-links/swagger`
   - `Anthropic Claude Documentation <https://docs.anthropic.com/>`_
