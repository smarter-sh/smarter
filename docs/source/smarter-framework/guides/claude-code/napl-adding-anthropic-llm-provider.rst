.. _napl-adding-anthropic-llm-provider:

How-To: Add an LLM Provider to Smarter (Anthropic)
==================================================

This how-to adds Anthropic as an LLM Provider on Northern Aurora Power & Light's (NAPL) Smarter
platform, so that Claude models, including ``claude-opus-5-5``, the model that Claude Code uses,
are available to LLMClients and to Claude Code. It is written for the platform administrator. The
companion tutorial for programmers is :doc:`napl-getting-started-claude-code`.

.. contents:: On this page
   :local:
   :depth: 1

Goal
----

Register Anthropic as an active Provider, with ``claude-opus-5-5`` among its models, using the
data points that Smarter requires. Smarter has a built-in definition of Anthropic, so the
shortest route is three commands. The longer route, a Provider manifest, is how you add any
provider that Smarter doesn't know, and it is shown here with Anthropic's values so that every
data point has a real example.

.. note::

   **Claude Code is a tool, not a model.** Claude Code is Anthropic's agentic coding tool. When it
   calls the Anthropic API, its default model is Claude Opus 5.5, whose model ID is
   ``claude-opus-5-5``. Wherever Smarter asks for a model, this how-to uses that ID.

Prerequisites
-------------

- A running Smarter platform. This how-to was checked against the source code of Smarter 0.33.11.
- A Smarter login with **staff** rights, to apply manifests, and a **superuser** login for the
  steps in Django Admin, at ``/admin/`` on your platform. The admin user that Smarter creates when
  the platform is initialized is both.
- The Smarter CLI, configured so that ``smarter whoami`` prints your user name.
- A shell in the Smarter application container (``smarter-app`` on a Docker install), for
  ``manage.py`` commands.
- An Anthropic API key, from https://platform.claude.com/settings/keys.

.. danger::

   Never commit an API key, or a manifest or ``.env`` file that contains one, to version control.

Concept Overview
----------------

Provider
   A company or service that hosts LLMs. A Provider record holds the base URL of the provider's
   API, the name of the Secret that holds the API key, links to the provider's public pages, and a
   verification status. Smarter uses only *active* Providers. See
   :doc:`/smarter-resources/smarter-provider`.

Provider model
   One model that a Provider offers, such as ``claude-opus-5-5``, with ``supports_*`` capability
   flags that Smarter tests.

Secret
   An encrypted credential. A Provider refers to its API key by the Secret's *name*, so the key
   never appears in a manifest. See :doc:`/smarter-resources/smarter-secret`.

Proxy
   Passthrough access to a Provider's API with the Provider's key, for callers who authenticate
   with a Smarter API key. This is how Claude Code reaches Anthropic through Smarter. See
   :doc:`/smarter-resources/smarter-proxy`.

**How Smarter calls a provider.** LLMClients send prompts through the OpenAI Python SDK, pointed
at the Provider's ``base_url``, so a Provider must offer an OpenAI-compatible Chat Completions
API. Anthropic offers one at ``https://api.anthropic.com/v1/``. Claude Code, on the other hand,
speaks Anthropic's native Messages API, so it goes through a Proxy, which forwards any path that
the Proxy allows.

**Two routes.** ``manage.py initialize_providers`` creates or updates the *built-in* Providers,
which include Anthropic, from API keys in the platform's environment. It runs whenever the
platform is initialized or deployed. Any other provider is added with a ``kind: Provider``
manifest, which an administrator completes in Django Admin and then verifies.

The Data Points
---------------

Each note starts with what needs the data point: **apply** means that ``smarter apply`` rejects
the manifest without it, **verification** means that the Provider can't become active without it,
and **prompts** means that prompts fail without it.

The Provider manifest
~~~~~~~~~~~~~~~~~~~~~

The fields below ``metadata`` go under ``spec.provider``. Their keys are snake_case, and
``smarter apply`` rejects a key that the Provider kind doesn't define, naming it, so ``baseUrl``
or ``model`` fails the apply. The complete manifest is in step 3 of Route B.

.. list-table::
   :header-rows: 1
   :widths: 27 28 45

   * - Field
     - Anthropic value
     - Notes
   * - ``metadata.name``
     - ``anthropic_claude``
     - **Apply.** The Provider's name: snake_case, up to 50 characters. LLMClients and Proxies
       refer to it, and it names the ``<NAME>_API_KEY`` environment variable (below).
   * - ``metadata.description``, ``metadata.version``
     - a sentence; ``1.0.0``
     - **Apply.** Both keys must be present.
   * - ``name``
     - ``anthropic_claude``
     - **Apply.** Lowercase letters, digits and underscores. Keep it equal to ``metadata.name``,
       which takes precedence.
   * - ``base_url``
     - ``https://api.anthropic.com/v1/``
     - **Prompts, verification.** The root of the OpenAI-compatible API, with its trailing slash.
   * - ``api_key``
     - ``anthropic_claude_api_key``
     - **Prompts, verification.** The *name* of a Secret that you own. The apply fails if no such
       Secret exists.
   * - ``connectivity_test_path``
     - ``/v1/models``
     - **Verification.** Smarter sends a ``GET`` request here, with the key as a bearer token, and
       requires HTTP 200. Write the full path from the host's root; Smarter adds the slashes.
   * - ``logo``
     - `Anthropic's logo on Wikimedia Commons
       <https://upload.wikimedia.org/wikipedia/commons/7/78/Anthropic_logo.svg>`__
     - **Verification.** A URL of at most 100 characters that ends in ``.svg``, ``.png``,
       ``.jpg`` or ``.jpeg``.
   * - ``website_url``
     - ``https://www.anthropic.com/``
     - **Verification.** Must return an HTML page with HTTP 200.
   * - ``terms_of_service_url``
     - `Anthropic's Commercial Terms of Service
       <https://www.anthropic.com/legal/commercial-terms>`__
     - **Verification.** An HTML page that contains the words "Terms of Service".
   * - ``docs_url``
     - `the Claude API overview <https://platform.claude.com/docs/en/api/overview>`__
     - **Verification.** An HTML page that contains the word "documentation".
   * - ``privacy_policy_url``
     - `Anthropic's Privacy Policy <https://www.anthropic.com/legal/privacy>`__
     - **Verification.** An HTML page that contains the words "Privacy Policy".
   * - ``contact_email``, ``support_email``
     - your team's addresses
     - **Verification.** Each also needs a *verified* date, set in Django Admin.

Set in Django Admin, not in the manifest
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 27 28 45

   * - Field
     - Value
     - Notes
   * - **Default model** (Provider)
     - ``claude-opus-5-5``
     - **Prompts.** Without it, every prompt to the Provider fails with
       ``default_model is required``, even when the LLMClient names a model.
   * - **Contact email verified**, **Support email verified**
     - the date you confirmed each address
     - **Verification.** Smarter doesn't send verification emails.
   * - **Tos accepted at**, **Tos accepted by**
     - now; your user
     - **Verification.** Who accepted the provider's terms for the platform, and when.
   * - **Provider model**: Name, ``supports_*`` flags
     - ``claude-opus-5-5``; text input, text generation, translation, summarization (the
       defaults) plus streaming and tools
     - Lists the model in Smarter and queues one live test per checked flag. Prompts send the
       model that the LLMClient names whether or not it has a record.

The environment
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 27 28 45

   * - Variable
     - Example
     - Notes
   * - ``SMARTER_ANTHROPIC_API_KEY``
     - ``sk-ant-...``
     - The built-in route. ``initialize_providers`` reads it, with or without the ``SMARTER_``
       prefix, and saves it in the Secret ``anthropic_api_key``.
   * - ``<NAME>_API_KEY``
     - ``ANTHROPIC_CLAUDE_API_KEY``
     - **Verification**, manifest route. The Provider's name in capitals. The *production API
       key* check reads only this unprefixed name, and the connectivity check prefers it to the
       Secret.

Setup
-----

Test the key before you give it to Smarter, with the request that Smarter's LLMClients make:

.. code-block:: console

   export ANTHROPIC_API_KEY='sk-ant-...'
   curl https://api.anthropic.com/v1/chat/completions \
     -H "Authorization: Bearer $ANTHROPIC_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model": "claude-opus-5-5", "max_completion_tokens": 256,
          "messages": [{"role": "user", "content": "Reply with one word: ready"}]}'

The reply is a Chat Completions object whose ``choices[0].message.content`` is Claude's answer.

Step-by-Step
------------

Route A: the built-in Anthropic Provider
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. Add the key to the platform's environment. On a Docker install, add it to ``.env`` at the root
   of the repository, then recreate the containers, since ``docker compose restart`` doesn't reread
   ``.env``:

   .. code-block:: console

      echo 'SMARTER_ANTHROPIC_API_KEY=sk-ant-...' >> .env
      docker compose up -d

   On Kubernetes, set ``SMARTER_ANTHROPIC_API_KEY`` in the Helm chart's values and deploy. The
   deployment's initialization job runs the next two steps for you.

#. Run the provider initialization:

   .. code-block:: console

      docker exec smarter-app python manage.py initialize_providers

   For Anthropic, it saves the key in the Secret ``anthropic_api_key``; creates the ``anthropic``
   Provider, verified and active, with the base URL ``https://api.anthropic.com/v1/`` and the
   default model ``claude-sonnet-4-6``; and lists Anthropic's models with the key, saving one
   Provider model for each, ``claude-opus-5-5`` among them. Each new model starts active, and
   its capability tests then run on the worker. The command is safe to repeat: an existing
   Provider keeps whatever status its verification, or an administrator, last gave it.

#. Apply the built-in Proxies. Platform initialization applies a built-in Proxy for each built-in
   Provider that has a key, and skips the ones that don't, so a platform initialized before the
   key was set has no ``anthropic`` Proxy until you run:

   .. code-block:: console

      docker exec smarter-app python manage.py add_example_proxies

   On Kubernetes, the initialization job runs this on every deploy too. The ``anthropic`` Proxy is
   what :doc:`napl-getting-started-claude-code` uses.

#. Confirm:

   .. code-block:: console

      smarter describe provider anthropic
      smarter get proxies

   The Provider's ``status`` section shows ``isVerified: true`` and ``isActive: true``, and the
   Proxies include ``anthropic``.

Route B: a Provider manifest, with Anthropic's values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Provider is named ``anthropic_claude``, not ``anthropic``: ``initialize_providers`` matches
Providers by name, and would take over one called ``anthropic`` on the next deploy.

#. **Save the key in a Secret.** Create ``anthropic-claude-api-key.yaml``, apply it, and delete
   the file, which holds the key in plain text:

   .. code-block:: yaml

      apiVersion: smarter.sh/v1
      kind: Secret
      metadata:
        name: anthropic_claude_api_key
        description: Anthropic API key for the anthropic_claude Provider
        version: 1.0.0
      spec:
        config:
          value: sk-ant-...

   .. code-block:: console

      smarter apply -f anthropic-claude-api-key.yaml && rm anthropic-claude-api-key.yaml

#. **Add the production key to the environment.** The verification's last check reads
   ``ANTHROPIC_CLAUDE_API_KEY``, so add it to ``.env`` and run ``docker compose up -d``, as in
   Route A.

#. **Write and apply the Provider manifest.** ``smarter manifest provider`` prints an example; its
   ``api_key`` looks like a key, but the field takes a Secret's name. Create
   ``anthropic-claude-provider.yaml`` with your team's email addresses:

   .. code-block:: yaml

      apiVersion: smarter.sh/v1
      kind: Provider
      metadata:
        name: anthropic_claude
        description: Anthropic's Claude models, through Anthropic's OpenAI-compatible API
        version: 1.0.0
      spec:
        provider:
          name: anthropic_claude
          base_url: https://api.anthropic.com/v1/
          api_key: anthropic_claude_api_key
          connectivity_test_path: /v1/models
          logo: https://upload.wikimedia.org/wikipedia/commons/7/78/Anthropic_logo.svg
          website_url: https://www.anthropic.com/
          terms_of_service_url: https://www.anthropic.com/legal/commercial-terms
          docs_url: https://platform.claude.com/docs/en/api/overview
          privacy_policy_url: https://www.anthropic.com/legal/privacy
          contact_email: llm-admin@example.com
          support_email: llm-support@example.com

   .. code-block:: console

      smarter apply -f anthropic-claude-provider.yaml

   Applying creates the record and nothing else: ``smarter describe provider anthropic_claude``
   shows ``isActive: false`` until verification passes.

#. **Complete the record in Django Admin**, as a superuser. Open **Providers →
   anthropic_claude** and set **Default model** to ``claude-opus-5-5``, the two **email
   verified** dates, **Tos accepted at** and **Tos accepted by**. Then open **Provider Models →
   Add**, with **Provider** ``anthropic_claude``, **Name** ``claude-opus-5-5``, **Is default**
   checked, and **Supports streaming** and **Supports tools** checked in addition to the defaults.
   Saving the model queues its capability tests.

#. **Run the verification.** Nothing starts it on its own:

   .. code-block:: console

      docker exec -it smarter-app python manage.py shell -c "
      from smarter.apps.provider.models import Provider
      from smarter.apps.provider.verification import verify_provider
      provider = Provider.objects.get(name='anthropic_claude')
      verify_provider(provider.id)
      provider.refresh_from_db()
      print(provider.status, provider.is_verified, provider.is_active)
      "

   The ten checks run in order and stop at the first failure: API connectivity, logo, contact
   email, support email, website, terms of service, documentation, privacy policy, terms
   acceptance, production API key. On success the command prints ``verified True True``, and
   Smarter activates the Provider; a passed check stays valid for 10 days.

   .. note::

      Anthropic's API requires an ``anthropic-version`` header on every request, which the
      connectivity check doesn't send, so for Anthropic expect the first check to fail. The check
      passes for providers whose models endpoint answers a plain ``GET``, such as OpenAI-compatible
      APIs. For Anthropic itself, use Route A, which creates the Provider verified.

Proof of Concept
----------------

#. ``smarter describe provider anthropic`` (or ``anthropic_claude``) shows ``isVerified: true``
   and ``isActive: true``.
#. In Django Admin, **Provider Models** lists ``claude-opus-5-5`` under the Provider with
   **Is active** checked. A test that fails because of the model clears the box; an error about
   the account, such as a bad key or no credit, leaves it as it was.
#. Apply an LLMClient that names the Provider and the model, and prompt it in the Workbench.
   Smarter notices a newly active Provider within 30 seconds, without a restart:

   .. code-block:: yaml

      apiVersion: smarter.sh/v1
      kind: LLMClient
      metadata:
        name: claude_check
        description: Checks the Anthropic Provider with the model that Claude Code uses
        version: 1.0.0
      spec:
        config:
          prompt:
            appName: Claude Check
            provider: anthropic
            defaultModel: claude-opus-5-5
            defaultTemperature: 1.0
            defaultMaxTokens: 16000

   Opus 5.5 returns HTTP 400 for any temperature other than ``1.0``, and its thinking counts
   against ``defaultMaxTokens``, so keep both values.

Troubleshooting
---------------

``Only account admins can apply provider manifests.``
   Your Smarter user isn't staff.

``Secret anthropic_claude_api_key not found``
   ``api_key`` must name a Secret that you own. Apply the Secret first.

``The Provider manifest has keys that it does not define: spec.provider.baseUrl``
   Keys are snake_case, and there is no ``model`` key. Rename or remove what the message names.

``initialize_providers`` prints ``ANTHROPIC_API_KEY is not set``
   The variable is missing from the containers' environment, or still a placeholder such as
   ``SET-ME-PLEASE``. The Provider is created anyway, without a key, and prompts to it fail until
   you set the key and run the command again.

Verification prints ``failed False False``
   In Django Admin, the Provider's **Provider Verifications** show each check; the failed one is
   the unsuccessful row with the latest **Updated at**. Usual causes: the Anthropic connectivity
   check (see the note above), a page without the expected words, or missing dates.

``Production API key for provider anthropic_claude was accessed but is not set``
   ``ANTHROPIC_CLAUDE_API_KEY`` isn't in the environment. The command stops without changing the
   Provider's status.

``anthropic is not a valid provider`` when applying an LLMClient
   The Provider isn't active yet, or became active in the last 30 seconds. Check it and retry.

``default_model is required``
   Set **Default model** on the Provider in Django Admin.

See Also
--------

- :doc:`napl-getting-started-claude-code`: the programmers' tutorial that uses this Provider.
- :doc:`/smarter-platform/adding-an-llm-provider`, :doc:`/smarter-resources/smarter-provider`,
  :doc:`/smarter-resources/provider/verification`
- `Models overview <https://platform.claude.com/docs/en/models/overview>`_ and
  `OpenAI SDK compatibility <https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/openai-sdk>`_,
  in Anthropic's documentation
