.. _napl-anthropic-admin-guide:

======================================================================
Getting Started: Enabling Claude Code on NAPL's Smarter Platform
======================================================================

.. contents:: Table of Contents
   :local:
   :depth: 2

.. note::

   This guide is for the **Smarter administrator**, who adds an LLM provider once
   on the platform. Programmers are not meant to complete these steps and should
   not be given the Anthropic API key.

   The steps and outputs in this guide were tested on 2026-10-11 and
   2026-10-12 on a local Docker Compose install of Smarter, built from source
   (development build).

Goal
====

We will use Claude Code with Smarter to give every programmer in NAPL's custom
programming area a Claude-backed coding assistant. The administrator supplies
one Anthropic API key to the central Smarter platform and enables Smarter's
built-in ``anthropic`` **Proxy**. Programmers then point Claude Code at that
proxy using their own personal Smarter API key.

.. list-table:: Who does what
   :header-rows: 1
   :widths: 25 75

   * - Role
     - Responsibility
   * - Administrator (you)
     - Add the Anthropic key to the platform, initialize the provider and the
       proxy, verify. Done once.
   * - Programmer
     - Needs a **staff** user account in Smarter. Sets two environment
       variables and runs ``claude``. No provider setup.

Prerequisites
=============

You are assumed to already have:

- A running Smarter platform, v0.16.0 or later (the Proxy feature).
- A Smarter **account administrator** login.
- Access to the platform's configuration and the ability to restart it and
  run management commands in its application container.
- An Anthropic API account with billing enabled. This is separate from a
  Claude subscription.
- Working knowledge of a Linux shell, YAML and environment variables.

Setup
=====

These steps prepare the administrator's workstation. Commands were run in a
WSL Ubuntu terminal.

1. Install the Smarter CLI
--------------------------

Download the Linux binary from the CLI's releases page and put it on your
``PATH``:

.. code-block:: bash

   curl -L -o smarter https://github.com/smarter-sh/smarter-cli/releases/download/v0.4.0/smarter-ubuntu-latest-0.4.0
   chmod +x smarter
   sudo mv smarter /usr/local/bin/smarter
   smarter version

2. Create a Smarter API key
---------------------------

The CLI authenticates with a Smarter API key. Create one for your admin user.
Replace the account number with your own:

.. code-block:: bash

   docker exec smarter-app python manage.py create_api_key \
     --account_number 1234-5678-9012 \
     --username admin \
     --description "CLI key for administration"

The 64-character key is printed once. Copy it immediately.

3. Write the CLI configuration file
-----------------------------------

Create ``~/.smarter/config.yaml``. Set ``environment`` to the environment you
are targeting (``local`` for a Docker install on your own machine):

.. code-block:: yaml

   config:
     account_number: 1234-5678-9012
     environment: local
     output_format: yaml
     root_domain: platform.smarter.sh
     username: admin
   local:
     api_key: <your 64-character Smarter API key>

4. Confirm the CLI can reach the platform
-----------------------------------------

.. code-block:: bash

   smarter whoami

The response should show your account, ``environment: local`` and
``isStaff: true`` for your user.

Concept Overview
================

**Provider**
   Smarter's record of an upstream LLM service. On a fresh install, Smarter
   already lists eight providers, including ``anthropic``, before any API key
   has been supplied. A provider cannot be used until its key is supplied.

**Secret**
   An encrypted value stored by Smarter. The Anthropic key is stored as a
   Secret named ``anthropic_api_key``. Other resources refer to it by name.

**Proxy**
   A pass-through endpoint for a provider's own API. A caller sends a normal
   Anthropic API request to Smarter with a **Smarter** API key. Smarter
   authenticates the caller, substitutes the platform's Anthropic key, forwards
   the request and records usage. Claude Code connects to this.

.. code-block:: text

   Claude Code  --(personal Smarter API key)-->  Smarter "anthropic" Proxy
                                                 --(platform Anthropic key)-->  Anthropic API

Why this design suits NAPL: one Anthropic key is held centrally, each
programmer has an individually revocable Smarter key, and each key records
when it was last used.

Data points Smarter needs
-------------------------

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

For Anthropic, only the two keys have to be supplied. Everything else is
built in.

.. note::

   Smarter's `Adding an LLM Provider
   <https://docs.smarter.sh/smarter-platform/adding-an-llm-provider.html>`__
   page describes writing and applying a ``Provider`` manifest for Anthropic.
   On the build tested here that was not necessary: ``anthropic`` was already
   listed, and supplying the key and running the commands in Step 4 was
   enough. Manifests remain the way to register a provider Smarter does not
   already list.

The proxy as a manifest
-----------------------

Every Smarter resource can be expressed as a YAML manifest. This is the proxy
Smarter creates, as returned by ``smarter describe proxy anthropic -o yaml``
(abbreviated):

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

Note that ``apiKey`` holds the **name** of the Secret, never the key itself.

Step-by-Step
============

The commands below are for a Docker Compose deployment. See
`On a production platform`_ for how the same steps map to Kubernetes.

Step 1: Obtain an Anthropic API key
-----------------------------------

Create a key in the `Claude Console <https://console.anthropic.com/>`__. A
valid key starts with ``sk-ant-api``.

Step 2: Add two settings to the platform configuration
------------------------------------------------------

In the ``.env`` file in the folder Smarter is started from, set both lines.
Each must have no leading ``#``:

.. code-block:: bash

   SMARTER_ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxx
   SMARTER_FERNET_ENCRYPTION_KEY=<generated value>

Generate the encryption key with:

.. code-block:: bash

   python3 -c "import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"

.. important::

   ``SMARTER_FERNET_ENCRYPTION_KEY`` must be set. The inline documentation
   in ``.env`` notes that if it is unset, a temporary key is generated at
   runtime. In testing, the proxy then could not decrypt the stored Anthropic
   key and failed with "its API key Secret anthropic_api_key cannot be read."

.. danger::

   Never commit ``.env`` to version control.

Step 3: Restart Smarter
-----------------------

Stop the running platform (``Ctrl+C`` in its terminal), then from the same
folder:

.. code-block:: bash

   make run

Confirm both settings reached the application container. Each command prints a
count and should print ``1``:

.. code-block:: bash

   docker exec smarter-app printenv | grep -c "ANTHROPIC_API_KEY"
   docker exec smarter-app printenv | grep -c "FERNET"

Step 4: Initialize the provider and the proxy
---------------------------------------------

.. code-block:: bash

   docker exec smarter-app python manage.py initialize_providers
   docker exec smarter-app python manage.py add_builtin_proxies

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

Step 6: Issue programmers their keys
------------------------------------

Smarter only issues API keys to **staff** users. A programmer's Smarter
account must be a staff account, or key creation fails with "API Keys can only
be created for staff users."

Create a key for each programmer, using their Smarter username:

.. code-block:: bash

   docker exec smarter-app python manage.py create_api_key \
     --account_number 1234-5678-9012 \
     --username <programmer username> \
     --description "Claude Code key for <name>"

The key is printed once, between two lines of asterisks. Send it to the
programmer securely.

.. note::

   In this deployment, the staff flag that allows API keys is also what
   Smarter checks before accepting Provider manifests. Review what staff
   users are permitted to change before granting staff accounts widely.

Step 7: Hand off to programmers
-------------------------------

Give each programmer the proxy address and their key. Their entire setup is:

.. code-block:: bash

   export ANTHROPIC_BASE_URL="http://<smarter-host>/api/v1/proxy/anthropic"
   export ANTHROPIC_API_KEY="<personal Smarter API key>"
   claude

On a local install the address is
``http://localhost:9357/api/v1/proxy/anthropic``. Do not append ``/v1``.

Claude Code asks once whether to use the key it found. Approve it. Without
these two variables, Claude Code uses its normal login instead.

No sharing step is needed: a staff user who is not the administrator can use
the built-in proxy as soon as their key exists.

On a production platform
------------------------

.. note::

   This section is based on Smarter's Helm chart and production deployment
   documentation. The steps in the rest of this guide were tested on a local
   Docker Compose install.

Production Smarter is deployed to Kubernetes with a Helm chart. The same
settings, ``SMARTER_ANTHROPIC_API_KEY`` and ``SMARTER_FERNET_ENCRYPTION_KEY``,
are set under ``env:`` in the chart's ``values.yaml`` and applied with
``helm upgrade``, which replaces the running application as a rolling update.
The chart's post-upgrade job runs platform initialization. Coordinate this
change with the infrastructure team.

Proof of Concept
================

The setup is complete when requests made with a **Smarter** API key, and no
Anthropic key on the caller's side, return real Claude responses.

1. List models through the proxy
--------------------------------

.. code-block:: bash

   export SMARTER_API_KEY="<your Smarter API key>"
   curl -s http://localhost:9357/api/v1/proxy/anthropic/v1/models \
     -H "x-api-key: $SMARTER_API_KEY" \
     -H "anthropic-version: 2023-06-01"

**Expected result:** JSON listing Anthropic's models, for example
``claude-haiku-4-5-20251001`` and ``claude-sonnet-4-5-20250929``.

2. Send a prompt through the proxy
----------------------------------

.. code-block:: bash

   curl -s http://localhost:9357/api/v1/proxy/anthropic/v1/messages \
     -H "x-api-key: $SMARTER_API_KEY" \
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

With the two variables from Step 7 set, start ``claude`` and type ``/status``.
It should report:

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
requests succeeding through Smarter.

4. Repeat as a programmer
-------------------------

Repeat tests 2 and 3 with a key issued to a staff user who is not the
administrator. In testing, a key for ``staff_user`` returned Claude's reply to
the ``curl`` prompt, and Claude Code ran successfully with it.

To confirm which key made the requests, list each key's last use:

.. code-block:: bash

   docker exec smarter-app python manage.py shell -c "
   from smarter.lib.drf.models import SmarterAuthToken
   for t in SmarterAuthToken.objects.all():
       print(t.name, '|', t.last_used_at)
   "

**Expected result:** the programmer's key shows a last-used time matching the
Claude Code requests in the log, and the administrator's key does not.

.. code-block:: text

   3141-5926-5359.staff_user | 2026-10-12 19:21:22
   3141-5926-5359.admin      | 2026-10-12 19:11:19

5. Revoke a programmer's key
----------------------------

Keys are managed in the Django admin, where they can be disabled or deleted.
Disable the programmer's key (untick **Is active**), then repeat the ``curl``
prompt with it, printing only the status code:

.. code-block:: bash

   curl -s -o /dev/null -w "HTTP %{http_code}\n" \
     http://localhost:9357/api/v1/proxy/anthropic/v1/messages \
     -H "x-api-key: $PROGRAMMER_KEY" \
     -H "anthropic-version: 2023-06-01" \
     -H "content-type: application/json" \
     -d '{"model": "claude-haiku-4-5-20251001", "max_tokens": 50,
          "messages": [{"role": "user", "content": "Reply with the word ready."}]}'

**Expected result:** ``HTTP 401``. The response has no body, so without the
status code the command appears to print nothing. The administrator's key and
every other programmer's key keep working.

Troubleshooting
===============

**The CLI's APT install fails with 403 Forbidden**
   The package repository has no build for newer Ubuntu releases. Remove it
   with ``sudo add-apt-repository --remove ppa:lpm0073/smarter-cli`` and
   install the binary as shown in Setup.

**"No api_key found for environment" when running smarter configure**
   The CLI checks for a saved key before ``configure`` can save one, so
   first-time setup fails. Write ``~/.smarter/config.yaml`` by hand as shown
   in Setup.

**"API Keys can only be created for staff users"**
   The user is not a staff user. Programmers need staff accounts to receive
   a Smarter API key.

**create_api_key prints no key**
   The command failed and its error was hidden. If you filtered the output
   with ``2>/dev/null``, rerun it with ``2>&1`` to see the error.

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

**smarter get providers returns HTTP 400 (invalid logo URL)**
   Seen on a local Docker install: provider logos are stored with a relative
   path that fails validation, so the provider list and the web console's
   Providers page fail. The providers still work. Verify with
   ``smarter get proxies`` and the Proof of Concept instead.

**A provider shows active and verified but does not work**
   On a fresh install, every listed provider already shows as active and
   verified before any key is supplied. Do not use those flags as evidence.
   Use the Proof of Concept.

**HEAD .../api/hello returns 401 in the log**
   This is Claude Code's startup connectivity check. It is harmless.

**Proxy returns 401 for a real request**
   The caller sent an invalid or disabled Smarter API key, no key at all, or
   an Anthropic key. The proxy only accepts active Smarter API keys.

**Unexpected Anthropic charges**
   Claude Code chooses its own default model, which may be the most expensive
   tier. All proxy usage is billed to the platform's Anthropic key. Choose a
   model with ``/model`` and consider Smarter budgets.

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

Acknowledgments
===============

This tutorial was prepared with assistance from Claude, an AI model made by
Anthropic. Claude helped research the Smarter documentation, diagnose errors
during testing, and draft the reStructuredText. All steps were run and
verified by the author on a local Docker installation of Smarter, and the
outputs shown are from that testing.
