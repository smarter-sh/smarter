.. _napl-getting-started-claude-code:

Getting Started: Claude Code with Smarter at NAPL
=================================================

This tutorial is for programmers at Northern Aurora Power & Light (NAPL). It takes you from a
Smarter login to a working Claude Code session that runs through NAPL's Smarter platform. The
platform-side setup that it relies on is in :doc:`napl-adding-anthropic-llm-provider`.

.. contents:: On this page
   :local:
   :depth: 1

Goal
----

We will use Claude Code with Smarter to write a small command-line tool, ``meter_totals.py``, that
reads a CSV file of hourly meter readings and prints each meter's total per day, with tests that
pass. Along the way you will configure Claude Code so that every request it makes goes through
Smarter: Anthropic's API key never leaves the platform, and your token usage is recorded against
your Smarter account.

Prerequisites
-------------

You can:

- sign in to NAPL's Smarter web console, ``https://platform.napl.example.com``, and you have a
  Smarter account (this tutorial uses that address; replace it with the one your platform team
  gave you),
- work in a terminal (Bash, Zsh or PowerShell), and have ``curl``,
- write Python 3 and run ``pytest``.

You do **not** need an Anthropic account or an Anthropic API key, and you do not sign in to
claude.ai. Smarter stands in for both.

Setup
-----

Install Claude Code
~~~~~~~~~~~~~~~~~~~

Claude Code runs on macOS 13 or later, Windows 10 1809 or later, and current Ubuntu, Debian and
Alpine releases. Run the installer for your system, then open a new terminal:

.. code-block:: console

   # macOS, Linux, WSL
   curl -fsSL https://claude.ai/install.sh | bash

   # Windows PowerShell
   irm https://claude.ai/install.ps1 | iex

Then confirm it:

.. code-block:: console

   claude --version

A working installation prints a version number followed by ``(Claude Code)``. If the shell can't find
``claude``, the install directory isn't on your ``PATH`` yet; ``claude doctor`` diagnoses this and
other install problems. Native installations update themselves in the background.

On Windows, Claude Code uses PowerShell for shell commands unless Git for Windows is installed,
in which case it uses Git Bash.

Get your Smarter API key
~~~~~~~~~~~~~~~~~~~~~~~~

Claude Code authenticates to Smarter with a Smarter API key, which identifies you. If your Smarter
user has the staff flag, create one yourself: in the web console, open **Account → API Keys**,
choose **New API Key** in the shortcut menu, click the **+** button beside it, and copy the key,
which is shown once. Otherwise, request one from the platform team. Store it where you keep other secrets, and never commit it to
a repository.

.. admonition:: For the platform team

   Create a key for a programmer in the Smarter application container. The command prints the
   key once:

   .. code-block:: console

      python manage.py create_api_key --username <programmer> --description "Claude Code"

   Smarter creates API keys only for users with the staff flag, so give the user that flag first.
   See :doc:`/smarter-platform/api-keys`.

Check the key and the Proxy
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Claude Code will talk to Smarter's built-in ``anthropic`` Proxy, at
``https://platform.napl.example.com/api/v1/proxy/anthropic``. Before you configure anything, make
the two requests that Claude Code will make. On Windows, run them in Git Bash, or use ``curl.exe``
in PowerShell.

#. List the Proxies that your key may use:

   .. code-block:: console

      export SMARTER_API_KEY='<your Smarter API key>'
      curl -sS -H "Authorization: Bearer $SMARTER_API_KEY" \
        https://platform.napl.example.com/api/v1/proxy/

   The reply is JSON with a ``proxies`` list. One entry has ``"name": "anthropic"``,
   ``"provider": "anthropic"``, ``"isActive": true``, and a ``url`` that ends in
   ``/api/v1/proxy/anthropic/``: that URL, without its trailing slash, is your base URL.

#. Send one message to Claude through it:

   .. code-block:: console

      curl -sS -w '\n%{http_code}\n' -X POST \
        https://platform.napl.example.com/api/v1/proxy/anthropic/v1/messages \
        -H "Authorization: Bearer $SMARTER_API_KEY" \
        -H "anthropic-version: 2023-06-01" \
        -H "content-type: application/json" \
        -d '{"model": "claude-opus-5-5", "max_tokens": 1024,
             "messages": [{"role": "user", "content": "Reply with one word: connected"}]}'

   A reply that starts with ``{"id":"msg_`` and ends with ``200`` means that your key, the Proxy
   and Anthropic all work. Anything else is explained in `Troubleshooting`_.

Point Claude Code at Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Claude Code reads two environment variables: ``ANTHROPIC_BASE_URL``, the gateway to send requests
to, and ``ANTHROPIC_AUTH_TOKEN``, a credential that it sends as ``Authorization: Bearer``, which is
the header that Smarter reads. Set both in the ``env`` block of your user settings file,
``~/.claude/settings.json`` (``%USERPROFILE%\.claude\settings.json`` on Windows), so that they
apply to every session and every project. Create the file if it doesn't exist:

.. code-block:: json

   {
     "env": {
       "ANTHROPIC_BASE_URL": "https://platform.napl.example.com/api/v1/proxy/anthropic",
       "ANTHROPIC_AUTH_TOKEN": "<your Smarter API key>"
     }
   }

Two details matter. The base URL ends at the Proxy's name, without ``/v1``: Claude Code adds
``/v1/messages`` itself. And the key goes in your *user* settings, never in a project's
``.claude/settings.json``, which is committed with the project.

Concept Overview
----------------

**What Smarter adds.** Smarter is NAPL's central LLM platform. Its administrators registered
Anthropic as a *Provider*, stored Anthropic's API key as a *Secret*, and share a *Proxy* named
``anthropic``: a passthrough to Anthropic's own API. You never hold Anthropic's key. You hold a
*Smarter API key*, which says who you are. Each request through the Proxy is charged, in tokens,
to you, to your account, to the Proxy and to the Provider, and a *Budget* can refuse requests once
a limit is reached. That is how the company tracks and caps what each team spends.

**How a request travels.**

.. code-block:: text

   Claude Code                         Smarter Proxy                        Anthropic
   -----------  Authorization: Bearer  -------------------  x-api-key: sk-ant-...  -------------
   POST .../api/v1/proxy/anthropic/v1/messages  ->  POST https://api.anthropic.com/v1/messages
                                      <-  server-sent events, streamed through as they arrive  <-

Claude Code speaks Anthropic's Messages API. With ``ANTHROPIC_BASE_URL`` set, it posts to
``<base URL>/v1/messages`` instead of ``api.anthropic.com``. Smarter checks your key, drops it,
adds Anthropic's key and the ``anthropic-version`` header, and forwards the body and Anthropic's
other headers unchanged, so streaming, tool use and prompt caching work as they do against
Anthropic directly. The Proxy allows only the paths that Claude Code needs: ``v1/messages``,
``v1/messages/count_tokens``, ``v1/models`` and ``v1/models/*``. When the stream ends, Smarter
reads the token counts from it and records the charge.

**Which model answers.** The Proxy forwards whatever model Claude Code asks for. Claude Code's
default is Claude Opus 5.5, model ID ``claude-opus-5-5``, which is why the Setup test used it.
``/model`` inside a session switches models, and the choice is sent to Anthropic unchanged.

**What goes where.** Your code reaches Smarter, and Anthropic, only inside prompts, as it would
if Claude Code talked to Anthropic directly. Claude Code's own usage telemetry goes to Anthropic
directly, not through Smarter; if NAPL policy requires, add ``"DISABLE_TELEMETRY": "1"`` to the
same ``env`` block.

Step-by-Step
------------

#. **Start Claude Code in a new project folder.**

   .. code-block:: console

      mkdir meter-totals && cd meter-totals
      git init
      claude

   Claude Code opens a session. It does not ask you to log in: your Smarter key takes the place
   of a claude.ai login. If it shows the login screen instead, see `Troubleshooting`_.

#. **Confirm where requests go.** Type ``/status``. The **Status** tab shows an ``Anthropic base
   URL`` line with your Proxy URL, and an ``Auth token`` line naming ``ANTHROPIC_AUTH_TOKEN``.

#. **Give Claude Code the task.** Paste this prompt:

   .. code-block:: text

      Create meter_totals.py, a command-line tool that reads a CSV file whose columns are
      meter_id, timestamp (ISO 8601) and kwh, and prints one line per meter per day:
      "<meter_id> <YYYY-MM-DD> <total kwh>", sorted by meter then date. Use only the standard
      library. Also create sample_readings.csv with two meters and two days of hourly readings,
      and test_meter_totals.py with pytest tests for the totals and for an empty file. Then run
      the tests.

   Claude Code proposes each file and each command before it acts. Read the diff, and press
   Enter to approve, or tell it what to change. Expect it to create the three files and run
   ``pytest``.

#. **Run the tests yourself**, outside the session, to see the result with your own eyes:

   .. code-block:: console

      python -m pytest -q

#. **Iterate.** Ask for a change, for example "also print a grand total per day across all
   meters", and watch it update the code and the tests. ``/cost`` shows the session's token usage
   so far, which is what Smarter records.

Proof of Concept
----------------

You are done when all three are true:

#. ``python -m pytest -q`` in ``meter-totals`` reports that the tests passed, and
   ``python meter_totals.py sample_readings.csv`` prints one line per meter per day.
#. ``/status`` shows your Proxy URL as the Anthropic base URL, and ``ANTHROPIC_AUTH_TOKEN`` as the
   credential, so the session ran through Smarter.
#. From the terminal, ``claude -p "Reply with one word: connected"`` prints ``connected``.

On the platform side, each request's tokens are charged to your user profile, your account, the
Proxy and the Provider, priced by provider and model. The platform team sees the charges in
Smarter's cost accounting.

Troubleshooting
---------------

``claude`` shows the login screen, or ``claude -p`` answers ``Not logged in``
   No credential reached the session. Check the settings file's JSON syntax with
   ``claude doctor``, and that the file is in your home directory, not in the project.

``Failed to authenticate. API Error: 401``, or ``401`` in the Setup test
   A credential was sent and rejected. A reply of ``{"detail": "Invalid token."}`` or
   ``{"detail": "Api key is not activated."}`` comes from Smarter: your key is wrong or inactive. A reply with ``"type": "authentication_error"`` comes
   from Anthropic: the key that the *platform* holds is wrong, which is for the platform team.
   Keep the key in ``ANTHROPIC_AUTH_TOKEN``, not ``ANTHROPIC_API_KEY``: the latter sends it as
   ``x-api-key``, which Smarter also accepts, but asks you to approve the key at every start.

``404`` with ``Proxy anthropic does not exist, or is not shared with you``
   The built-in Proxy isn't applied on this platform, or your account can't read it. Ask the
   platform team; the Proxy needs the Anthropic Provider and its Secret, as described in
   :doc:`napl-adding-anthropic-llm-provider`.

``403`` with ``does not allow the path``
   Your base URL is wrong. It must end in ``/api/v1/proxy/anthropic``, with no ``/v1`` after it;
   ``.../anthropic/v1`` makes Claude Code ask for ``v1/v1/messages``.

``402`` with ``a budget forbids more charges``
   A Smarter Budget's limit was reached, for you, your account or the Proxy. Ask the platform team.

``502``, ``503`` or ``504`` with ``smarter_proxy_error``
   Smarter couldn't reach Anthropic, the Proxy has no key, or Anthropic took longer than the
   Proxy's timeout. The ``message`` field says which. ``503`` is for the platform team.

An error naming ``claude-opus-5-5``
   Opus 5.5 needs Claude Code 2.1.280 or later: run ``claude update``. If Anthropic reports the
   model as not found, pick another with ``/model``.

Claude Code sits with no output for minutes, or shows the spinner but never answers
   Either the base URL is wrong or unreachable, in which case Claude Code retries quietly with
   backoff, or something between you and Smarter buffers the stream. Repeat the Setup test with
   ``"stream": true`` in the JSON and ``-N`` on ``curl``: ``data:`` lines should arrive one by
   one. No reply points at the URL; a reply that arrives all at once points at a proxy or ingress
   in between, for the platform team.

``/fast`` says fast mode is disabled, or Remote Control is unavailable
   Expected behind a gateway. Neither affects coding.

See Also
--------

- :doc:`napl-adding-anthropic-llm-provider`: how the platform team registered Anthropic.
- :doc:`/smarter-resources/smarter-proxy` and :doc:`/smarter-platform/api-keys`
- `Connect Claude Code to an LLM gateway <https://code.claude.com/docs/en/llm-gateway-connect>`_
  and `Advanced setup <https://code.claude.com/docs/en/setup>`_, in the Claude Code documentation
