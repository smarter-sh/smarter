Getting Started with Claude Code at NAPL
========================================

.. contents:: On this page
   :local:
   :depth: 2

Goal
----

We will use Claude Code with Smarter to pair-program on NAPL's software: you drive, Claude Code proposes, and every
request is governed, attributed and cost-tracked by Smarter. We call this a CoPilot coding pair: a programmer paired
with Claude Code as an AI pair programmer. Claude Code reaches Anthropic through a Smarter Proxy, so you use your own Smarter API key and never hold
the Anthropic key.

.. note::

   "CoPilot coding pairs" here means a programmer paired with Claude Code. It has nothing to do with GitHub Copilot.

Prerequisites
-------------

- A Smarter account, and a personal Smarter API key from the Smarter administrator.
- The Smarter host URL and the Proxy name, also from the administrator. This guide uses the lab values
  ``http://localhost:9357`` and ``napl_claude_code``.
- A Linux or macOS shell.
- Network access to Smarter.

Setup
-----

1. Store your Smarter key
~~~~~~~~~~~~~~~~~~~~~~~~~

Create a file that only you can read, then paste the key into it with an editor. Never commit the key or paste it into
a chat.

.. code-block:: console

   install -m 600 /dev/null ~/.smarter_api_key

2. Install Claude Code
~~~~~~~~~~~~~~~~~~~~~~

Download the installer, inspect it, then run it:

.. code-block:: console

   curl -fsSL https://claude.ai/install.sh -o claude-install.sh
   less claude-install.sh
   bash claude-install.sh
   claude --version

3. Configure Claude Code
~~~~~~~~~~~~~~~~~~~~~~~~

Create ``~/.claude/settings.json`` **before** the first run:

.. code-block:: json

   {
     "env": {
       "ANTHROPIC_BASE_URL": "http://localhost:9357/api/v1/proxy/napl_claude_code",
       "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
     },
     "apiKeyHelper": "cat ~/.smarter_api_key",
     "model": "claude-haiku-5-5"
   }

Replace the URL with the host and Proxy name your administrator gave you.

Concept Overview
----------------

.. code-block:: text

   Claude Code  ->  Smarter Proxy  ->  https://api.anthropic.com

- A **Provider** is Smarter's record of an LLM vendor, here Anthropic.
- A **Secret** is a credential that Smarter stores encrypted. The Anthropic key lives in one.
- A **Proxy** is an authenticated pass-through to the vendor's API. It checks your Smarter key, removes it, and adds the
  Anthropic key from the Secret before forwarding. Every request is logged with your Smarter user.

Administrators set these up; see :doc:`napl-howto-anthropic-claude-code-proxy`.

What each setting does:

- ``ANTHROPIC_BASE_URL`` points Claude Code at the Proxy. It has no ``/v1`` suffix, because Claude Code appends
  ``/v1/messages`` itself.
- ``apiKeyHelper`` is a command that Claude Code runs to get its credential, so the key stays in the mode-600 file.
- ``CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`` stops nonessential outbound traffic.
- ``model`` sets a low-cost default. Use ``claude-sonnet-5-5`` for harder work.

Do not log in to a Claude account. With ``apiKeyHelper`` set, Claude Code uses your Smarter key and shows no login.

**Cost awareness.** In the lab validation, each Claude Code request carried roughly 23,000 to 30,000 input tokens of
system prompt, tool definitions and repository context such as ``CLAUDE.md``. Prompt caching makes repeated context much
cheaper. Your figures will differ.

Step-by-Step
------------

1. Run a smoke test:

   .. code-block:: console

      claude -p "Reply with exactly: Claude Code via Smarter OK"

   It should print ``Claude Code via Smarter OK``.

2. Start an interactive session in a project folder:

   .. code-block:: console

      cd <your-project-folder>
      claude

3. Confirm Manual mode. Claude Code may default to Auto mode, which approves actions that pass its own safety check.
   For pair programming, use Manual mode, which asks before each edit. Check the mode indicator, and switch with
   ``Shift+Tab``.

4. Review each proposed edit before you approve it. You remain the programmer; Claude Code is the pair.

5. Run ``/cost`` to see the session cost.

6. Optional, VS Code: the integrated terminal and the Claude Code extension published by Anthropic both read
   ``~/.claude/settings.json``, so both route through Smarter. In the extension, use the mode selector to set Manual
   mode. IDE integration is owned by the IDE tooling team. GitHub Copilot Chat is a different product and does not route
   through Smarter.

Proof of Concept
----------------

.. code-block:: console

   mkdir -p ~/napl-poc && cd ~/napl-poc && claude

Give Claude Code this prompt:

.. code-block:: text

   Create calc.py with a function add(a, b) that has a Google-style docstring, and test_calc.py with a pytest test for
   it. Then run the test.

In Manual mode, Claude Code asks before it writes the two files and before it runs the test, and you approve each step.

In the lab validation the test passed (``test_calc.py::test_add PASSED``). ``/cost`` reported $0.0065 on
``claude-haiku-5-5``, with 85% of input tokens served from the prompt cache. Those are results from one run, not
guarantees. The request also appeared in the Smarter Proxy log under the programmer's Smarter user.

Troubleshooting
---------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Symptom
     - Check
   * - Requests fail
     - ``ANTHROPIC_BASE_URL`` must be ``<smarter-host>/api/v1/proxy/<proxy-name>`` with no ``/v1`` suffix.
   * - Authentication fails
     - ``~/.smarter_api_key`` may be missing, empty, wrong or revoked. Confirm that it exists with mode 600.
   * - An endpoint is refused
     - The path is not in the Proxy's ``allowedPaths``. Ask the Smarter administrator.
   * - Claude Code asks you to log in
     - ``settings.json`` is missing or is not valid JSON, or has no ``apiKeyHelper``. Do not log in; fix the settings.
   * - Anthropic reports a low credit balance
     - This is an administrator issue (credit or spend limit). Contact the Smarter administrator.
   * - Unknown model
     - List the available models through the Proxy's ``/v1/models`` endpoint.
