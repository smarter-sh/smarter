.. _napl-anthropic-admin-guide:

================================================================
Getting Started: Enabling Claude Code on NAPL's Smarter Platform
================================================================

.. contents:: Table of Contents
   :local:
   :depth: 2

.. note::

   This guide is for a **Smarter administrator**. Enabling Anthropic and its proxy
   is done once on the platform by an administrator. Programmers should never hold an
   Anthropic API key.

   Note that steps and outputs in this guide were tested on a local Docker Compose
   install of Smarter v0.18.11, built from source, with Smarter CLI v0.4.0. The steps
   on a production platform have been provided based on Smarter documentation, but
   have not been tested.

Goal
====

We will use Claude Code with Smarter to give every programmer in NAPL's custom
programming area a coding assistant.

Prior to Smarter v0.14.17, adding Anthropic meant applying a provider manifest, which is
what `Adding an LLM Provider
<https://docs.smarter.sh/smarter-platform/adding-an-llm-provider.html>`__ covers. For
providers that Smarter does not list, the steps in that guide are still relevant. As of
Smarter v0.14.17, Anthropic is one of Smarter's built-in providers; therefore,
using Anthropic means supplying an API key and initializing the built-in provider
and proxy, which is what the steps below help with.

Prerequisites
=============

You are assumed to have the following:

- A running Smarter platform, v0.16.0 or later (includes the Proxy feature).
- A Smarter administrator-level account that can login to the Smarter
  web console.
- The `Smarter CLI <https://docs.smarter.sh/smarter-framework/smarter-cli.html>`__
  installed and configured with your own Smarter administrator API key.
- Permission to change the platform's configuration and apply it (redeploy in production;
  restart on a local Docker install), and the ability to run management commands
  in the Smarter application container.
- `Claude Code <https://code.claude.com/docs/en/setup>`__ installed to test
  the proxy as a programmer would.
- Python 3 for generating a Fernet encryption key.
- An Anthropic API account with billing enabled.
- A bash-compatible terminal (e.g., Linux, macOS, or WSL) and working knowledge
  of YAML and environment variables. The commands in this guide use bash syntax.

Setup
=====

Confirm the Smarter CLI can reach the platform using your Smarter administrator API key:

.. code-block:: bash

   smarter whoami

The response should show your account and ``"isStaff": true`` for your user. Staff status
is required for the administrator to add a provider and issue Smarter API keys to
programmers.

Concept Overview
================

**Provider**
   Smarter's record of an upstream LLM service. Since v0.14.17, Smarter
   lists eight providers, including Anthropic. To use one of these providers,
   a provider API key must be supplied.

**Secret**
   An encrypted value stored by Smarter. The Anthropic key is stored as a
   Secret named ``anthropic_api_key``. Other resources refer to it by name.

**Proxy**
   A pass-through endpoint for a provider's own API. A caller sends a normal
   Anthropic API request to Smarter with a Smarter API key. Smarter
   authenticates the caller, substitutes the platform's Anthropic key, forwards
   the request and records usage. Claude Code connects to the proxy.

.. figure:: _data/napl-claude-code-proxy-flow.svg
   :alt: Claude Code sends requests to Smarter's Anthropic proxy with the
         programmer's Smarter key. The proxy checks the key, swaps in the
         company's Anthropic key, forwards the request to Anthropic, and
         passes Claude's reply back.
   :width: 100%
   :align: center

   One request through Smarter's Anthropic proxy.

With this pattern, one Anthropic key is held centrally, and each
programmer has an individually revocable Smarter key. Each key records
when it was last used.

Configuration Data
==================

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Data point
     - Value for Anthropic
     - Supplied by
   * - API key
     - ``SMARTER_ANTHROPIC_API_KEY``
     - Administrator, in the platform configuration
   * - Encryption key for stored secrets
     - ``SMARTER_FERNET_ENCRYPTION_KEY``
     - Administrator, in the platform configuration
   * - Secret holding the key
     - ``anthropic_api_key``
     - Smarter, when the provider is initialized
   * - Upstream API
     - ``https://api.anthropic.com/``
     - Smarter (built-in proxy)
   * - Proxy address
     - ``/api/v1/proxy/anthropic/``
     - Smarter (built-in proxy)
   * - Authentication header
     - ``x-api-key``
     - Smarter (built-in proxy)

For Anthropic, the administrator supplies only two values: the Anthropic API
key (``SMARTER_ANTHROPIC_API_KEY``) and the encryption key Smarter uses to
store it (``SMARTER_FERNET_ENCRYPTION_KEY``). Smarter provides everything
else.

Step-by-Step
============

Step 1: Obtain an Anthropic API key
-----------------------------------

Create a key in the `Claude Console <https://console.anthropic.com/>`__. A
valid key starts with ``sk-ant-api``.

Step 2: Add two settings to the platform configuration
------------------------------------------------------

Generate a Fernet encryption key for Smarter to use when storing the Anthropic key:

.. code-block:: bash

   python3 -c "import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"

.. important::

   ``SMARTER_FERNET_ENCRYPTION_KEY`` must be set. The inline documentation
   in ``.env`` notes that if it is unset, a temporary key is generated at
   runtime. In testing, the proxy was unable to decrypt the stored Anthropic
   key and failed with "its API key Secret anthropic_api_key cannot be read."

In the ``.env`` file in the folder Smarter is started from, set both lines.

.. code-block:: bash

   SMARTER_ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxx
   SMARTER_FERNET_ENCRYPTION_KEY=<generated value>

**Production:** set the same two values under ``env:`` in the Helm chart's
``values.yaml``.

Step 3: Apply the configuration
-------------------------------

For a local install, stop the running platform (``Ctrl+C`` in its terminal).
Then, from the same folder, run the following:

.. code-block:: bash

   make run

Confirm both settings reached the application container. Both commands below
should print ``1``:

.. code-block:: bash

   docker exec smarter-app printenv | grep -c "ANTHROPIC_API_KEY"
   docker exec smarter-app printenv | grep -c "FERNET"

**Production:** apply the changed values with ``helm upgrade``, which replaces
the running application as a rolling update. Coordinate this change with the
infrastructure team.

Confirm both settings reached the application pod. The Helm chart's
``values.yaml`` defines both settings with placeholder values, so these
commands check the values themselves rather than whether the variables exist.
Use the ``namespace`` and ``global.appName`` values from ``values.yaml``. Both
commands below should print ``1``:

.. code-block:: bash

   kubectl exec -n <namespace> deploy/<appName> -- printenv SMARTER_ANTHROPIC_API_KEY | grep -c "^sk-ant-api"
   kubectl exec -n <namespace> deploy/<appName> -- printenv SMARTER_FERNET_ENCRYPTION_KEY | grep -vc "SET-ME"

Step 4: Initialize the provider and the proxy
---------------------------------------------

.. code-block:: bash

   docker exec smarter-app python manage.py initialize_providers
   docker exec smarter-app python manage.py add_builtin_proxies

**Production:** the Helm chart's post-upgrade job runs platform
initialization. To run the commands yourself, run them in the application pod.

The second command reports which proxies it created. Only providers with a key
get one:

.. code-block:: text

   Applied Proxy anthropic.
   Skipped Proxy cohere: its Provider or API key Secret does not exist.
   Skipped Proxy openai: its Provider or API key Secret does not exist.
   ...

Step 5: Verify the proxy exists
-------------------------------

.. code-block:: bash

   smarter get proxies

Before Step 4 this table is empty. Afterwards it contains one row named
``anthropic`` with ``isActive`` true.

Like every Smarter resource, the proxy can be expressed as a YAML manifest.
To see the one Smarter created:

.. code-block:: bash

   smarter describe proxy anthropic -o yaml

**Expected result** (abbreviated):

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Proxy
   metadata:
     annotations:
     - smarter.sh/proxy/builtin: "true"
     description: Passthrough access to Anthropic's Messages API, for Claude.
     name: anthropic
     version: 1.0.0
   spec:
     allowedPaths:
     - v1/messages
     - v1/messages/count_tokens
     - v1/models
     - v1/models/*
     apiKey: anthropic_api_key
     auth:
       header: x-api-key

Note that ``apiKey`` holds the name of the Secret, never the key itself.

Step 6: Create a Smarter API key for each programmer
----------------------------------------------------

Create a key for each programmer, using their Smarter username and your
account number (``accountNumber`` in the ``smarter whoami`` output):

.. code-block:: bash

   docker exec smarter-app python manage.py create_api_key \
     --account_number <account number> \
     --username <programmer username> \
     --description "Claude Code key for <name>"

The key is printed once, between two lines of asterisks. Copy it immediately,
as it will not be shown again.

**Production:** run the same command in the application pod.

Step 7: Hand off to programmers
-------------------------------

Give each programmer the proxy address and their key. Their entire setup is:

.. code-block:: bash

   export ANTHROPIC_BASE_URL="http://<smarter-host>/api/v1/proxy/anthropic"
   export ANTHROPIC_API_KEY="<personal Smarter API key>"
   claude

Without these two variables, Claude Code uses its normal login instead.

On a local install the address is
``http://localhost:9357/api/v1/proxy/anthropic``. Do not append ``/v1``.
Claude Code adds ``/v1/messages`` to the base URL itself, so an extra ``/v1``
produces ``.../v1/v1/messages``, which the proxy rejects with ``403``.

.. important::

   The first time a programmer runs ``claude`` with these variables set,
   Claude Code asks whether to use the API key it found in the environment.
   The programmer should approve it. Claude Code remembers the answer, so a
   programmer who declines by mistake is not asked again and the key is not
   used.


.. note::

   All proxy usage is billed to the platform's Anthropic key. Claude Code
   chooses its own default model, which may be the most expensive tier, so
   tell programmers which model to choose with ``/model``, and consider
   Smarter budgets.

Proof of Concept
================

The setup is complete when a programmer's Smarter API key, with no Anthropic
key on the programmer's side, returns real Claude responses. Run these tests
as a programmer would: with a key issued in Step 6 to a staff user who is not
the administrator.

.. code-block:: bash

   export PROGRAMMER_KEY="<Smarter API key issued in Step 6>"

1. List models through the proxy
--------------------------------

.. code-block:: bash

   curl -s https://localhost:9357/api/v1/proxy/anthropic/v1/models \
     -H "x-api-key: $PROGRAMMER_KEY" \
     -H "anthropic-version: 2023-06-01"

**Expected result:** JSON listing Anthropic's models, for example
``claude-haiku-4-5-20251001`` and ``claude-sonnet-4-5-20250929``.

2. Send a prompt through the proxy
----------------------------------

.. code-block:: bash

   curl -s http://localhost:9357/api/v1/proxy/anthropic/v1/messages \
     -H "x-api-key: $PROGRAMMER_KEY" \
     -H "anthropic-version: 2023-06-01" \
     -H "content-type: application/json" \
     -d '{"model": "claude-haiku-4-5-20251001", "max_tokens": 50,
          "messages": [{"role": "user", "content": "Reply with the word ready."}]}'

**Expected result** (abbreviated):

.. code-block:: json

   {
     "model": "claude-haiku-4-5-20251001",
     "type": "message",
     "role": "assistant",
     "content": [{"type": "text", "text": "ready"}],
     "stop_reason": "end_turn",
     "usage": {"input_tokens": 13, "output_tokens": 4}
   }

3. Run Claude Code through the proxy
------------------------------------

Set the two variables from Step 7, using the programmer's key:

.. code-block:: bash

   export ANTHROPIC_BASE_URL="http://localhost:9357/api/v1/proxy/anthropic"
   export ANTHROPIC_API_KEY="$PROGRAMMER_KEY"
   claude

Approve the key when Claude Code asks, then type ``/status``. It should
report:

.. code-block:: text

   Auth token:          claude.ai · not in use
   API key:             ANTHROPIC_API_KEY
   Anthropic base URL:  http://localhost:9357/api/v1/proxy/anthropic

Send a short prompt, then confirm the requests in Smarter's log:

.. code-block:: bash

   docker logs smarter-app --tail 400 2>&1 | grep "proxy/anthropic" | grep "HTTP/1.1" | tail -n 8

**Expected result:**

.. code-block:: text

   "GET /api/v1/proxy/anthropic/v1/models HTTP/1.1" 200
   "POST /api/v1/proxy/anthropic/v1/messages HTTP/1.1" 200
   "HEAD /api/v1/proxy/anthropic/api/hello HTTP/1.1" 401
   "POST /api/v1/proxy/anthropic/v1/messages?beta=true HTTP/1.1" 200

The lines ending ``?beta=true`` with status ``200`` are Claude Code's
requests succeeding through Smarter. The ``HEAD .../api/hello`` line with
status ``401`` is Claude Code's startup connectivity check, and is harmless.

4. Confirm the programmer's key made the requests
-------------------------------------------------

List each key's last use:

.. code-block:: bash

   docker exec smarter-app python manage.py shell -c "
   from smarter.lib.drf.models import SmarterAuthToken
   for t in SmarterAuthToken.objects.all():
       print(t.name, '|', t.last_used_at)
   "

**Expected result:** the programmer's key shows a last-used time matching the
Claude Code requests in the log, and the administrator's key does not
(abbreviated):

.. code-block:: text

   3141-5926-5359.staff_user | 2026-10-12 19:21:22
   3141-5926-5359.admin      | 2026-10-12 19:11:19

Troubleshooting
===============

**"API Keys can only be created for staff users"**
   The user is not a staff user. Programmers need staff accounts to receive
   a Smarter API key.

**Proxy error: "its API key Secret anthropic_api_key cannot be read"**
   Smarter cannot decrypt the stored key. Set
   ``SMARTER_FERNET_ENCRYPTION_KEY``, restart, and rerun both commands in
   Step 4 so the key is stored again.

**A setting does not reach the container (the count in Step 3 is 0)**
   Check that the line in ``.env`` has no leading ``#``, that the file was
   saved, that it is the ``.env`` in the folder Smarter starts from, and that
   Smarter was restarted afterwards.

**smarter get proxies does not list anthropic**
   The proxy is only created when the Anthropic key is configured. Confirm
   Steps 2 and 3, then rerun Step 4.

**A provider shows active and verified but does not work**
   On a fresh install, every listed provider already shows as active and
   verified before any key is supplied. Do not use those flags as evidence.
   Use the Proof of Concept.

**Proxy returns 401 for a real request**
   The caller sent an invalid or disabled Smarter API key, no key at all, or
   an Anthropic key. The proxy only accepts active Smarter API keys.

References
==========

Smarter documentation:

- `Smarter Proxy <https://docs.smarter.sh/smarter-resources/smarter-proxy.html>`__
- `Adding an LLM Provider to Smarter <https://docs.smarter.sh/smarter-platform/adding-an-llm-provider.html>`__
- `Smarter Provider <https://docs.smarter.sh/smarter-resources/smarter-provider.html>`__
- `API Keys <https://docs.smarter.sh/smarter-platform/api-keys.html>`__
- `Smarter CLI <https://docs.smarter.sh/smarter-framework/smarter-cli.html>`__
- `Quick Start Guide <https://docs.smarter.sh/smarter-platform/installation/quick-start.html>`__
- `Production Deployment <https://docs.smarter.sh/smarter-platform/installation/production-deployment.html>`__
- `Configuration <https://docs.smarter.sh/smarter-platform/configuration.html>`__
- The inline documentation in Smarter's ``.env`` file
- `Smarter v0.16.0 release notes <https://github.com/smarter-sh/smarter/releases/tag/v0.16.0>`__
- `Smarter CLI repository and releases <https://github.com/smarter-sh/smarter-cli>`__

Anthropic documentation, for the Claude Code side:

- `Claude Code: Advanced setup <https://code.claude.com/docs/en/setup>`__
- `Claude Code: LLM gateways <https://code.claude.com/docs/en/llm-gateway>`__
