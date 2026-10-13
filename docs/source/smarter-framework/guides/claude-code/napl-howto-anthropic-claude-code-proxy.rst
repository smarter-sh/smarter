Adding Anthropic as an LLM Provider for Claude Code
====================================================

.. contents:: On this page
   :local:
   :depth: 2

Overview
--------

This guide is for Smarter platform administrators at Northern Aurora Power & Light (NAPL). It sets up a
gateway so that NAPL programmers can use Claude Code while the Anthropic API key is stored once, in Smarter, and never
handed to programmers.

.. code-block:: text

   Claude Code  ->  Smarter Proxy  ->  https://api.anthropic.com

Three Smarter resources make this work:

- A **Provider** is a Smarter record of an LLM vendor: its name, base URL and contact details. See
  :doc:`/smarter-resources/smarter-provider`.
- A **Secret** is an encrypted credential that Smarter stores and that other resources reference by name. Here it
  holds the Anthropic API key. See :doc:`/smarter-resources/smarter-secret`.
- A **Proxy** is an authenticated pass-through to an upstream HTTP API. Callers present a Smarter API key. The Proxy
  verifies it, removes it, and injects the Anthropic key from the Secret before forwarding the request. See
  :doc:`/smarter-resources/smarter-proxy`.

The Proxy accepts the caller's Smarter key as ``Authorization: Bearer``, as ``Authorization: Token`` or as
``x-api-key``, and strips every credential header before forwarding. Every request is logged with its method, path,
status, latency, token usage, model and the Smarter user.

What Smarter Needs
------------------

.. list-table::
   :header-rows: 1
   :widths: 14 24 62

   * - Resource
     - Field
     - Value or purpose
   * - Provider
     - ``name``
     - ``anthropic``
   * - Provider
     - ``base_url``
     - ``https://api.anthropic.com/v1/``
   * - Provider
     - ``api_key``
     - Not used in this setup. The seeded Provider has no key set; the Proxy injects the key from the Secret.
   * - Provider
     - ``description``, ``connectivity_test_path``, ``logo``, ``website_url``, ``contact_email``, ``support_email``,
       ``terms_of_service_url``, ``docs_url``, ``privacy_policy_url``
     - Provided by Smarter's built-in Provider. No change is needed.
   * - Secret
     - ``metadata.name``
     - ``anthropic_api_key``
   * - Secret
     - ``spec.config.value``
     - The Anthropic API key, ``<your-anthropic-api-key>``
   * - Secret
     - ``spec.config.expiration_date``
     - Matches the key's expiry in the Anthropic Console
   * - Proxy
     - ``metadata.name``
     - ``napl_claude_code``. It becomes part of the Proxy URL.
   * - Proxy
     - ``spec.provider``
     - The Provider's name: ``anthropic``
   * - Proxy
     - ``spec.apiKey``
     - The Secret's name: ``anthropic_api_key``
   * - Proxy
     - ``spec.baseUrl``
     - ``https://api.anthropic.com/``, without a trailing ``/v1/``
   * - Proxy
     - ``spec.auth``
     - Header ``x-api-key`` with an empty scheme, which is how Anthropic expects its key
   * - Proxy
     - ``spec.headers``
     - ``anthropic-version: "2023-06-01"``
   * - Proxy
     - ``spec.allowedPaths``
     - The only endpoints the Proxy forwards. Every other path is refused.
   * - Proxy
     - ``spec.timeout``
     - ``600`` seconds, to allow long Claude Code turns
   * - Proxy
     - ``spec.isActive``
     - ``true``

Step-by-Step
------------

1. Create the Anthropic API key
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the Anthropic Console (`platform.claude.com <https://platform.claude.com/>`_):

- Create an API key scoped to a single workspace, with an expiry date.
- Set a monthly spend limit and alert thresholds for that workspace.
- Keep auto-reload off, so that the spend limit stays the real ceiling.

.. note::

   A Claude subscription (claude.ai) is not an API key. Claude Code through the Proxy needs an Anthropic Console API
   key.

2. Create the Secret
~~~~~~~~~~~~~~~~~~~~

Save the following as ``anthropic-secret.yaml``, replacing the placeholder with the key from step 1:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Secret
   metadata:
     name: anthropic_api_key
     description: Anthropic API key used by Smarter to proxy Claude Code
     version: 1.0.0
   spec:
     config:
       value: <your-anthropic-api-key>
       expiration_date: "2027-01-31T00:00:00Z"   # match the key's expiry in the Anthropic Console

Apply it:

.. code-block:: console

   smarter apply -f anthropic-secret.yaml

Keep this file out of version control, and delete it once it is applied.

3. Confirm the Anthropic Provider
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Smarter seeds a built-in ``anthropic`` Provider with the base URL ``https://api.anthropic.com/v1/``. No change is
needed: the Proxy references the Provider by name.

4. Create the Proxy
~~~~~~~~~~~~~~~~~~~

Save the following as ``napl_claude_code.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Proxy
   metadata:
     name: napl_claude_code
     description: "NAPL: Claude Code gateway to Anthropic via Smarter"
     version: 1.0.0
   spec:
     provider: anthropic
     apiKey: anthropic_api_key
     baseUrl: https://api.anthropic.com/
     auth:
       header: x-api-key
       scheme: ""
     headers:
       anthropic-version: "2023-06-01"
     allowedPaths:
       - v1/messages
       - v1/messages/count_tokens
       - v1/models
       - v1/models/*
     timeout: 600
     isActive: true

Apply it:

.. code-block:: console

   smarter apply -f napl_claude_code.yaml

.. important::

   ``baseUrl`` must **not** end in ``/v1/``. Claude Code appends ``/v1/messages`` to its ``ANTHROPIC_BASE_URL``. A Proxy
   whose ``baseUrl`` is ``https://api.anthropic.com/v1/``, as in Smarter's example Proxy manifest, forwards to
   ``/v1/v1/messages``, and its ``allowedPaths`` entry ``messages`` would not match ``v1/messages``.

``allowedPaths`` is also a control: the Proxy refuses any endpoint that is not listed.

The Proxy URL has the form ``<smarter-host>/api/v1/proxy/<proxy-name>/``. In the lab it is
``http://localhost:9357/api/v1/proxy/napl_claude_code/``.

5. Issue programmer API keys
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each programmer gets their own Smarter API key. Create it with:

.. code-block:: console

   docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py create_api_key --account_number <account-number> --username <username>"

The key is shown once. Deliver it to the programmer through a secure channel, never by email or chat.

One key per programmer is what makes per-user attribution and single-person offboarding work. Do not share keys.

Then give each programmer the Smarter host, the Proxy name and their key.

Verify
------

Use your own Smarter API key, stored in ``~/.smarter_api_key``. The outputs below come from the lab validation of this
setup.

List the models through the Proxy:

.. code-block:: console

   curl -s http://localhost:9357/api/v1/proxy/napl_claude_code/v1/models \
     -H "Authorization: Bearer $(cat ~/.smarter_api_key)"

In the lab this returned a JSON list of models, including ``claude-haiku-5-5``, ``claude-sonnet-5-5`` and
``claude-opus-5-5``.

Send a small message:

.. code-block:: console

   curl -s http://localhost:9357/api/v1/proxy/napl_claude_code/v1/messages \
     -H "Authorization: Bearer $(cat ~/.smarter_api_key)" \
     -H "Content-Type: application/json" \
     -d '{"model":"claude-haiku-5-5","max_tokens":20,"messages":[{"role":"user","content":"Reply with exactly: NAPL proxy OK"}]}'

In the lab the response content text was ``NAPL proxy OK``.

Confirm that the request was logged. This command applies to a Docker Compose installation such as the lab:

.. code-block:: console

   docker logs smarter-app 2>&1 | grep "Proxy napl_claude_code"

In the lab the log line was:

.. code-block:: text

   Proxy napl_claude_code: POST v1/messages -> 200 in 1.05s, usage Usage(prompt_tokens=25, completion_tokens=11, total_tokens=36, model='claude-haiku-5-5'), for <user>

The latency and token counts are from that one request and will differ in your environment.

Governance Notes
----------------

- **Spend control.** The spend limit and alert thresholds at Anthropic are the outer cap on cost, whatever happens
  inside Smarter.
- **Key expiry and rotation.** Rotate the Anthropic key in the Console, then update the Secret only. Programmer
  workstations do not change.
- **Attribution.** Each request is logged with the Smarter user who made it.
- **Endpoint control.** ``allowedPaths`` limits what the Proxy forwards. Add a path only when there is a need for it.
- **Offboarding.** Revoke a programmer's Smarter API key to cut off that one person. Nobody else is affected.
- **Reconciliation (recommendation).** Compare Smarter's usage with the Anthropic Console periodically. In the lab, the
  Proxy log reported ``prompt_tokens`` without a prompt-cache breakdown, and the Console's cost view lagged real usage,
  so neither is a complete record on its own.

.. seealso::

   Programmers: see :doc:`napl-getting-started-claude-code-proxy` to set up and use Claude Code through this Proxy.
