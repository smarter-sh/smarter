Adding Anthropic as an LLM Provider
===================================

Goal
----

Make Anthropic available through Northern Aurora Power & Light's (NAPL)
Smarter platform and prepare an endpoint for Claude Code.

This gives NAPL's programmers access to Claude for AI-assisted coding,
with credentials and usage managed centrally through Smarter.

Prerequisites
-------------

* A running Smarter platform with Proxy support enabled (v0.16.0 or later).
* An administrator account permitted to manage Provider resources.
* The Smarter CLI installed and authenticated to that platform.
* An organization-approved Anthropic API key with API access.
* Network access from Smarter to ``https://api.anthropic.com``.

Infrastructure deployment, IDE integration, and accounting setup are
handled by other teams.

Configuration overview
----------------------

Anthropic provides the Claude models used by the Claude Code assistant.
Three Smarter resources manage access:

* **Secret:** stores the organization's Anthropic API key.
* **Provider:** describes Anthropic and references its credential.
* **Proxy:** forwards the programmer's API requests to Anthropic.

.. code-block:: text

   Claude Code -> NAPL Smarter proxy -> Anthropic's Claude API

Programmers use personal Smarter API keys; Smarter supplies the Anthropic
credential. Claude remains hosted by Anthropic. The proxy created below
is shared with programmers in your Smarter account.

.. note::

   If approved Anthropic access is already configured, reuse it and skip
   to step 4. Check with ``smarter get providers`` and ``smarter get proxies``.

1. Store the Anthropic credential
---------------------------------

Obtain the API key through NAPL's approved Anthropic account. Create a
private ``napl-anthropic-secret.yaml`` file outside your Git repository:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Secret
   metadata:
     name: napl_anthropic_api_key
     description: Anthropic credential for NAPL
     version: 1.0.0
   spec:
     config:
       value: "<replace privately with the Anthropic API key>"

1. Replace the placeholder locally with the Anthropic API key.
2. Upload the file using the web console's manifest drop zone and apply it.
3. Confirm that the Secret was created in your account.
4. Remove the temporary file according to NAPL's credential-handling policy.

.. warning::

   This file contains a plaintext credential. Keep it out of Git and
   screenshots. Other manifests reference only the Secret's name.

2. Register the provider
------------------------

Save this non-secret configuration as ``napl-anthropic-provider.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: napl_anthropic
     description: Anthropic access for NAPL
     version: 1.0.0
   spec:
     provider:
       name: napl_anthropic
       base_url: https://api.anthropic.com/v1/
       api_key: napl_anthropic_api_key
       website_url: https://www.anthropic.com/
       docs_url: https://platform.claude.com/docs/en/api/overview

``api_key`` names the Secret from step 1. Keep ``metadata.name`` and
``spec.provider.name`` identical; these resource names use underscores.

Apply the manifest and inspect the saved resource:

.. code-block:: console

   smarter apply -f napl-anthropic-provider.yaml
   smarter describe provider napl_anthropic

Applying the manifest registers the configuration; it does not mark the
provider as verified or active. Step 4 checks API access through the proxy.

3. Configure the Anthropic proxy
--------------------------------

Save ``napl-anthropic-proxy.yaml`` to forward Anthropic's native API
requests using the stored credential:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Proxy
   metadata:
     name: napl_anthropic
     description: Anthropic API access for NAPL programmers
     version: 1.0.0
   spec:
     provider: napl_anthropic
     apiKey: napl_anthropic_api_key
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
     timeout: 300
     isActive: true

Apply and inspect it:

.. code-block:: console

   smarter apply -f napl-anthropic-proxy.yaml
   smarter describe proxy napl_anthropic

Unlike the Provider's ``base_url``, this proxy's ``baseUrl`` omits
``v1/`` because incoming requests include it. ``allowedPaths`` limits
the endpoints callers may use.

To reuse the built-in provider, set ``spec.provider`` to ``anthropic``
and retain your account's Secret reference.

4. Verify access
----------------

Copy the proxy URL from ``smarter describe``:

.. code-block:: text

   https://<NAPL-Smarter-host>/api/v1/proxy/napl_anthropic/

In a Bash-compatible shell with curl 7.76 or later, set:

* ``SMARTER_PROXY_URL``: the proxy URL copied above.
* ``SMARTER_API_KEY``: your personal Smarter key, populated securely.

List the available models through the proxy:

.. code-block:: bash

   curl --fail-with-body "${SMARTER_PROXY_URL%/}/v1/models" \
     -H "x-api-key: $SMARTER_API_KEY" \
     -H "anthropic-version: 2023-06-01"

Set ``CLAUDE_MODEL`` to an exact, approved ID from the response, then send
a small request, which consumes API tokens:

.. code-block:: bash

   curl --fail-with-body "${SMARTER_PROXY_URL%/}/v1/messages" \
     -H "x-api-key: $SMARTER_API_KEY" \
     -H "anthropic-version: 2023-06-01" \
     -H "Content-Type: application/json" \
     -d "{\"model\":\"$CLAUDE_MODEL\",\"max_tokens\":32,\"messages\":[{\"role\":\"user\",\"content\":\"Reply with Hello NAPL.\"}]}"

A successful response contains a message ID, text in ``content``, and
token ``usage``. This verifies basic proxy access. Test streaming, token
counting, and tool use in Claude Code before onboarding programmers.

Troubleshooting
---------------

* **Secret missing or 503:** check its name, account ownership, value,
  and expiration.
* **401:** check whether Smarter rejected the caller's key or Anthropic
  rejected the stored credential.
* **404 or blocked path (403):** check the proxy URL and ``allowedPaths``;
  avoid duplicating ``v1/`` in the upstream URL.
* **Unavailable model:** use an exact ID from ``GET v1/models`` that your
  organization may access.

Handoff to programmers
----------------------

Give programmers the proxy URL, individual Smarter credentials, and
approved model ID for :doc:`napl-getting-started-claude-code`.

References
----------

* :doc:`Smarter Provider </smarter-resources/smarter-provider>`
* :doc:`Smarter Proxy </smarter-resources/smarter-proxy>`
* :doc:`Smarter Secret </smarter-resources/smarter-secret>`
* `Anthropic Models API
  <https://platform.claude.com/docs/en/api/models/list>`_
* `Claude Code gateway connections
  <https://code.claude.com/docs/en/llm-gateway-connect>`_

AI assistance disclosure
------------------------

This tutorial was drafted and revised with assistance from OpenAI Codex.
