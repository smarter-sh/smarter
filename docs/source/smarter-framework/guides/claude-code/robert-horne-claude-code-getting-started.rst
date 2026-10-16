==========================================
Getting Started: Claude Code with Smarter
==========================================

Goal
====

Northern Aurora Power & Light (NAPL) wants its programmers
to use Claude Code as an AI programming assistant through
the company's Smarter platform.

This tutorial explains the intended setup and shows how
to test the connection with a simple programming task.

.. attention::

   Claude Code integration with Smarter is a prerelease
   feature. The steps described here have not yet been
   verified to work end to end.

Prerequisites
=============

Before starting, you will need:

- A Smarter account with permission to use Anthropic.
- Access to the Anthropic proxy in Smarter.
- Claude Code installed on your workstation.
- A Smarter API credential authorized for proxy access.
- A project folder where you can safely test Claude Code.

Your administrator must provide the proxy URL and
approved authentication method. Do not use an
administrator's API key or share credentials.

Setup
=====

Before configuring Claude Code, confirm that Smarter
already provides access to Anthropic.

1. Log in to Smarter.
2. Open Providers and find ``anthropic``.
3. Open Proxies and find the Anthropic proxy.
4. Ask your administrator to confirm that your account
   is authorized to use the proxy.

If Anthropic is missing, follow our companion guide:

:doc:`robert-horne-adding-anthropic-provider`

Your administrator must also confirm that the Smarter
proxy supports the authentication method required by
Claude Code. Do not assume that a working proxy
automatically means Claude Code is supported.

Concept Overview
================

Three components work together:

- **Claude Code:** The programming assistant running
  on your workstation.
- **Smarter:** The company platform that manages access
  to the AI provider through its proxy.
- **Anthropic:** The provider that runs the Claude models.

The intended request path is:

::

   Programmer
       |
   Claude Code
       |
   Smarter Anthropic Proxy
       |
   Anthropic Claude Model

Smarter manages the upstream Anthropic credentials.
Programmers should use only credentials approved for
their own accounts.

Step-by-Step: Connect Claude Code
=================================

1. Open a terminal in your test project folder.

2. Set the Smarter proxy address:

   .. code-block:: bash

      export ANTHROPIC_BASE_URL="https://YOUR-SMARTER-HOST/api/v1/proxy/anthropic/"

   Replace ``YOUR-SMARTER-HOST`` with the address
   supplied by your administrator.

3. Configure authentication using your approved
   Smarter credential.

   Claude Code supports two common methods:

   - ``ANTHROPIC_AUTH_TOKEN`` for bearer-token authentication.
   - ``ANTHROPIC_API_KEY`` for API-key authentication.

   Ask your administrator which method the Smarter
   proxy accepts. Do not guess or use an Anthropic
   provider key in place of your Smarter credential.

4. Start Claude Code:

   .. code-block:: bash

      claude

5. Inside Claude Code, enter:

   .. code-block:: text

      /status

   Check that the Anthropic base URL points to Smarter
   and that the expected authentication method is active.

   A correct URL alone does not prove the connection works.
   A successful request is still required.

Proof of Concept
================

We will use a simple Python program to test whether
Claude Code can assist with programming through Smarter.

1. Create a new folder for testing:

   .. code-block:: bash

      mkdir claude-test
      cd claude-test

2. Start Claude Code:

   .. code-block:: bash

      claude

3. Ask Claude Code:

   .. code-block:: text

      Create a Python program named hello.py that
      prints "Hello from NAPL!".
      Explain the code before making changes.

4. Review the proposed changes and approve them
   only if they are appropriate.

5. Run the program:

   .. code-block:: bash

      python hello.py

   Expected output:

   .. code-block:: text

      Hello from NAPL!

6. Confirm that Claude Code completed the request
   using the Smarter proxy.

A working Python program alone is not proof of
Smarter integration. The request must also be
confirmed in Smarter's available logs or usage records.

Troubleshooting
===============

**Claude Code cannot connect**

Check the proxy URL and network connection.
Confirm that the Smarter proxy supports the
authentication method used by Claude Code.

**Authentication failed**

Check that your Smarter credential is valid and
authorized for the Anthropic proxy. Never share
credentials when requesting support.

**Anthropic provider unavailable**

Contact your Smarter administrator or follow
the companion provider setup guide.

**Model not available**

Ask your administrator which Claude models are
available through the Smarter proxy.

**Claude Code uses Anthropic directly**

Check ``ANTHROPIC_BASE_URL`` and confirm that it
points to the Smarter proxy rather than Anthropic.

**Program does not run**

Review the generated code and Python error messages.
A programming error does not necessarily indicate
a problem with Smarter.

References
==========

- :doc:`robert-horne-adding-anthropic-provider`
- :doc:`/smarter-platform/adding-an-llm-provider`
- `Claude Code documentation <https://code.claude.com/docs/en/overview>`_



