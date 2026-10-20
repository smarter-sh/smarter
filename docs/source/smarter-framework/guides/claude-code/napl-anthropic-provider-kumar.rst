Adding Anthropic for NAPL's Claude Code pilot
=============================================

Goal
----

Enable Anthropic in Northern Aurora Power & Light's existing Smarter platform
and publish a native Anthropic API endpoint for Claude Code users

This guide targets the Provider initializer and Proxy resource present in this
repository, rather than assuming that every older Smarter installation has
them — confirm the deployed version before beginning

Prerequisites
-------------

* A deployed Smarter platform with HTTPS and the Proxy API enabled
* A platform administrator who owns the built-in resources, an authenticated
  Smarter CLI, and an operator able to run existing management commands
* An approved Anthropic API credential with access to the chosen Claude model
* Familiarity with YAML, HTTP authentication, environment variables and git

Platform installation, IDE integration and accounting code configuration belong
to the other project teams and are outside this tutorial

Concept overview
----------------

Anthropic is the provider, ``claude-sonnet-4-6`` is the example model identifier,
and Claude Code is the programming client — ``claude-code`` is not a model ID

A Provider describes the upstream service, a Secret holds its credential, and
a Proxy forwards the client's native Anthropic requests through Smarter
Developers authenticate to the Proxy with their own Smarter API keys
The Anthropic credential remains on the server

Hosting Smarter on premises does not host Claude's model weights locally
Prompts and relevant source code still travel from Smarter to Anthropic, so use
only the synthetic exercise in the companion tutorial for the initial pilot

Setup
-----

Use the :doc:`Smarter CLI <../../smarter-cli>` configured for the NAPL platform
Run the configuration wizard if this machine has not been configured, then
check the selected account and version

.. code-block:: console

   smarter configure
   smarter whoami
   smarter version
   smarter resources

Confirm that ``Provider``, ``Secret`` and ``Proxy`` are available
If Proxy is absent, ask the infrastructure team to provide a compatible
deployment before continuing

.. list-table:: Required integration values
   :header-rows: 1
   :widths: 35 65

   * - Setting
     - Value or source
   * - Provider name
     - ``anthropic``
   * - Provider API base URL
     - ``https://api.anthropic.com/v1/``
   * - Server credential setting
     - ``SMARTER_ANTHROPIC_API_KEY`` supplied through the deployment's secret store
   * - Secret created by initialization
     - ``anthropic_api_key``
   * - Proxy name and upstream base URL
     - ``napl_claude`` and ``https://api.anthropic.com/``
   * - Upstream authentication
     - ``x-api-key`` with no prefix, plus ``anthropic-version: 2023-06-01``
   * - Developer credential
     - An individual Smarter API key, never the shared Anthropic key
   * - Model ID
     - ``claude-sonnet-4-6``, subject to API availability and NAPL approval

Step-by-step
------------

1. Initialize the provider and its models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Obtain the approved API key from the
`Anthropic Console <https://platform.claude.com/>`_
Have the deployment operator inject it as ``SMARTER_ANTHROPIC_API_KEY`` into
the existing application environment and reload that environment through the
normal deployment process
Do not put the value in this repository or a command committed to git

Inside that application's existing runtime, from the directory containing
``manage.py``, the operator runs

.. code-block:: console

   python manage.py initialize_providers

The current initializer includes Anthropic: it stores the credential in a
Secret, creates or updates ``anthropic``, and discovers models through the
Anthropic models API
It also initializes other built-in providers, so this is an operator task
Review its Anthropic output for credential or discovery errors

Using a CLI authenticated as the owner of the initialized resources, inspect
the provider

.. code-block:: console

   smarter describe provider anthropic

The :doc:`Provider schema <../../../smarter-resources/provider/manifest/models>`
places connection details in ``spec.provider``, including ``name``,
``base_url``, ``api_key`` and ``connectivity_test_path``
Here ``api_key`` means a Secret's name, not its plaintext value
The schema also supports provider description, website, documentation, contact,
support, logo, terms and privacy details, populated by the built-in initializer

Do not add ``spec.provider.model`` or create one Provider per Claude model
The current Provider schema has no ``model`` field
Model catalog entries are separate ProviderModel records, and native Proxy
requests choose the model in their request body

.. note::

   Registration and a reported active or verified status are not an end-to-end
   test — newly initialized built-in providers can have those flags before a
   successful inference request, while existing disabled providers retain
   their state
   Resolve disabled or failed verification with the administrator, then use
   the acceptance checks below

2. Create the Claude Code endpoint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As the same resource owner, save the following as ``napl-claude-proxy.yaml``
This uses the field names accepted by the
:doc:`Proxy schema <../../../smarter-resources/proxy/manifest>`

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Proxy
   metadata:
     name: napl_claude
     description: Native Anthropic access for the NAPL coding pilot
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
     timeout: 300
     isActive: true

The Proxy base URL deliberately excludes ``/v1/`` because Claude Code adds it
The path list permits inference, token counting and model discovery
It restricts endpoints, not model IDs — model selection in a client is not a
server-enforced model allowlist

.. code-block:: console

   smarter validate -f napl-claude-proxy.yaml
   smarter apply -f napl-claude-proxy.yaml
   smarter describe proxy napl_claude

The provider must be visible to the Proxy owner, and the Secret must belong to
that owner's account
A platform-owned Proxy is shared across accounts in Smarter, so use this
ownership model only for NAPL's dedicated company platform

Give the pilot developers the HTTPS Proxy URL reported by ``describe``, the
approved model ID and the instructions for obtaining a personal Smarter key
The URL has the form
``https://YOUR-SMARTER-HOST/api/v1/proxy/napl_claude/``
This is a placeholder to replace with the actual deployment address

Proof of concept and go-live decision
-------------------------------------

Use a developer's account to complete
:doc:`Getting started <napl-claude-code-kumar>`
Its model-list and message checks must succeed through this exact Proxy,
and its coding exercise must pass all seven tests

Before extending the pilot, the platform owner checks these additional cases

* ``POST v1/messages/count_tokens`` returns an integer ``input_tokens`` for a
  request containing the approved model and a user message
* A streaming ``POST v1/messages`` with ``stream: true`` returns
  ``Content-Type: text/event-stream`` and completes through ``message_stop``
* A coding session can read a file, propose an edit, obtain approval and finish
  a tool-result round trip without losing Anthropic headers or message blocks
* An invalid Smarter key receives 401, and ``GET v1/files`` with a valid key
  receives 403 with ``path_not_allowed``
* The platform records the pilot's usage against the expected caller and
  account, and the accounting team confirms its existing cost configuration

The native Proxy implementation supports this routing design, but the
repository's Claude Code guide labels the integration prerelease
These are required acceptance criteria, not a claim that the NAPL deployment
has already passed them
Record the platform version, Claude Code version and test outcomes before the
project owner authorizes wider onboarding

If the pilot fails, change ``spec.isActive`` to ``false`` in
``napl-claude-proxy.yaml`` and apply it again
This disables the pilot endpoint without deleting its configuration
Investigate the failure and repeat the acceptance checks before re-enabling it

Troubleshooting
---------------

.. list-table:: Common setup failures
   :header-rows: 1
   :widths: 30 70

   * - Symptom
     - Action
   * - Anthropic is present but prompts fail
     - Confirm the initializer received a real credential and the model is
       accessible — registration can exist without a working key
   * - Secret not found or wrong account
     - Apply as the owner of ``anthropic_api_key`` or provision an approved
       Secret in the intended Proxy owner's account
   * - Manifest validation failure
     - Compare against ``smarter json-schema proxy`` and the deployed version,
       checking field spelling, indentation and required metadata
   * - 401
     - Distinguish a rejected developer Smarter key from an upstream Anthropic
       authentication error — the two credentials serve different hops
   * - 403 with ``proxy_inactive`` or ``path_not_allowed``
     - Check ``isActive``, the allowed paths and accidental duplicate ``v1``
   * - 404 or unknown model
     - Check the Proxy name and model-list response, then confirm the approved
       model with the administrator
   * - 402, 429, 502, 503 or 504
     - Inspect the error body for budget lock, rate limit, network failure,
       missing or expired Secret, or upstream timeout before retrying

The :doc:`Smarter Proxy reference <../../../smarter-resources/smarter-proxy>`
explains authentication, stream forwarding and error codes
The `Claude Code gateway compatibility guide
<https://code.claude.com/docs/en/llm-gateway-protocol>`_ defines the client-side
protocol requirements to recheck when upgrading
