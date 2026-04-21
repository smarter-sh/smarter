Smarter Claude Code Plugin
=========================================

This tutorial helps you quickly onboard by configuring **Claude Code** as an LLM provider in **Smarter**. It enables you to build features, fix bugs, and automate development tasks by understanding your entire codebase. You’ll also learn how to set up **Claude Code** and API Keys within the **Smarter** platform.

.. note::
   You should complete this tutorial for a smooth development experience. Proper configuration of **LLM providers** and **API keys** is essential for Smarter to function correctly. By following the steps outlined in this tutorial, your development environment will be fully prepared to use **Claude Code** for prompt generation, testing, and feature development within **Smarter**.

.. contents:: Table of Contents
   :local:
   :depth: 2


Goal
-----------------------------------------

We will use the Smarter platform / CLI to register Claude Code as an LLM provider, wire it to a new ChatBot, deploy the ChatBot, and verify end-to-end operation by sending prompts through smarter platform. We will also validate Claude Code API responses via ``curl`` (terminal command) and/or postman (GUI client).

By the end of this tutorial you will have:

- A ``Secret`` manifest storing your Anthropic API key securely in Smarter.
- A ``ChatBot`` manifest backed by ``claude-code-1-0``.
- A local development environment configured to use the Claude provider for prompt generation and testing.
- A live, publicly accessible ChatBot framework through Smarter platform returning Claude Code responses.


Prerequisites
-----------------------------------------

Before you start with setting up the Claude code plugin, ensure you have the following prerequisites in place:

.. list-table:: System Requirements
   :widths: 30 70
   :header-rows: 1

   * - Functional Areas
     - Requirements
   * - System Requirements
     - A compatible operating system (Linux, macOS, or Windows with WSL2) and necessary permissions to install software and set environment variables. Please refer System Requirements.
   * - Smarter Platform
     - Set smarter development environment by following steps in Getting Started with Smarter Development Environment.
   * - API Keys
     - Valid API keys for both Smarter and Claude Code. You will need these to authenticate and access the respective services. Follow instructions in API Keys to generate and manage your smarter API keys, and obtain your Claude Code API key from the `Claude Code API Key <https://code.claude.com/docs/en/overview>`__.
   * - REST API Validation Tool
     - Install ``postman`` client if you would like to test claude code with GUI otherwise you should be comfortable using ``curl`` terminal command to verify claude code API responses.
   * - Proxy Setting
     - Smarter proxies requests to external providers; your prompts and completions travel from Smarter's on-premise inference gateway to Anthropic's API over TLS. Ensure your network egress policy allows outbound HTTPS to ``api.anthropic.com:443`` before proceeding.

.. admonition:: Other Requirements
   :class: important

    **You should also have:**

    - Familiarity with command-line interfaces (CLI) and basic terminal commands.
    - Basic understanding of LLMs and API interactions.
    - A code editor (e.g., VS Code, PyCharm) for editing configuration files and writing test scripts.
    - Basic knowledge of JSON, YAML and Python for working with Smarter configurations and test scripts.
    - Internet connectivity to access Smarter services and the Anthropic API.
    - A Smarter account with appropriate permissions to create providers and manage API keys.
    - Access to the Smarter documentation for reference during setup and troubleshooting.


Setup
-------

Step 1 — Install the Smarter CLI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Smarter CLI is a Go binary — no runtime dependencies. Download the appropriate binary for your platform from smarter platform website.
The cli implements a set of verbs for working with Smarter resources. Refer to the Smarter CLI Reference for detailed command usage and examples.

.. code-block:: text

   https://smarter.sh/cli

After installation verify if smarter CLI is working by running:

.. code-block:: bash

   smarter --version

Configure the CLI with your credentials by running below command:

.. code-block:: bash

   smarter --configure

The interactive prompt will ask for your Smarter API key and account number.
These are written to ``$HOME/.smarter/config.yaml``, which you can also edit
directly. The file structure looks like:

.. code-block:: yaml

   config:
     account_number: 3141-5926-5359    # your account number
     environment: <ENVIRONMENT>        # e.g., prod, staging
     output_format: yaml
   prod:
     api_key: <SMARTER-API-KEY>

Confirm the CLI is authenticated by running below command:

.. code-block:: bash

   smarter --whoami

You should see your account details returned as JSON or YAML.

Step 2 — Create a Working Directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   mkdir smarter-tutorial && cd smarter-tutorial


Step 3 — Set the Claude API Key as an Environment Variable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Smarter retrieves authentication credentials from environment variables. Set the Claude API key as an environment variable on your system using below commands

.. warning::

   Never commit API keys to version control. Use ``.gitignore`` or a secrets manager to keep them out of your repository.

**Linux / macOS**

.. code-block:: bash

   export CLAUDE_API_KEY=<YOUR_CLAUDE_API_KEY>

**Windows (PowerShell)**

.. code-block:: powershell

   setx CLAUDE_API_KEY "<YOUR_CLAUDE_API_KEY>"

After setting the variable, restart your terminal or development environment to ensure the variable is available to Smarter.


Step 4 — Create the Claude Provider Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Smarter uses provider configuration files to define
how external LLM services are accessed.

Navigate to the provider configuration directory:

.. code-block:: text

   smarter/providers/

Create a new configuration file:

.. code-block:: text

   claude_provider.yaml

Add the following configuration:

  .. code-block:: yaml

    provider:
      name: claude
      type: anthropic

    model:
      name: claude-code-1-0
      temperature: 0.2

    authentication:
       api_key_env: YOUR_CLAUDE_API_KEY

This configuration instructs Smarter to:

- Use Claude as an LLM provider
- Authenticate using the environment variable
- Send requests to the Claude model


Step 6 — Register the Claude Provider in Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After creating the provider configuration,
Claude must be registered so that Smarter
can recognize and use it.

Locate the provider registry file:

.. code-block:: text

   smarter/providers/__init__.py

Add the Claude provider to the registry:

.. code-block:: python

   from smarter.providers.claude import ClaudeProvider

   PROVIDERS = {
       "claude": ClaudeProvider
   }

This step makes the Claude provider available
for use within the Smarter framework.


Step 7 — Verify Environment Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Confirm that the Claude API key is correctly set.

**Linux / macOS**

.. code-block:: bash

   echo $CLAUDE_API_KEY

**Windows (PowerShell)**

.. code-block:: powershell

   echo %CLAUDE_API_KEY%

If correctly configured, the command will display
the API key value.


Step 8 — Validate Claude Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run a simple test request to confirm that
Smarter can communicate with Claude.

Example test script:

.. code-block:: python

   from smarter.llm import generate

   prompt = "Explain recursion in one sentence."

   response = generate(
       provider="claude",
       prompt=prompt
   )

   print(response)

If successful, Claude will return a response, confirming that the integration is working.

.. important::

  After completing the setup check the below:

    - The Claude API key is configured.
    - Claude is registered as an LLM provider.
    - Smarter can authenticate with Claude.
    - The development environment is ready to use Claude for prompt generation, testing, and feature development.



Integration Concept Overview
-----------------------------------------

This section explains the key ideas that underpin integrating Claude as an LLM provider in Smarter. Understanding these concepts before working through the setup steps will help you make informed decisions during configuration and troubleshoot issues more effectively.


.. _concept-llm-providers:

LLM Providers
~~~~~~~~~~~~~

An **LLM provider** is an external service that hosts and serves a large language model via an API. When you send a prompt through Smarter, the platform routes that request to a registered provider, receives the model's completion, and returns it to your application. Smarter is designed to be provider-agnostic — you can swap or add providers (such as Claude, OpenAI, or others) without changing your application logic.

Claude, developed by Anthropic, is one such provider. It exposes its models through the Anthropic API at ``api.anthropic.com``. Smarter communicates with this endpoint on your behalf, abstracting away the provider-specific HTTP calls behind a unified interface.

.. _concept-smarter-gateway:

The Smarter Gateway
~~~~~~~~~~~~~~~~~~~~

The **Smarter gateway** is an on-premise inference proxy that sits between your development environment (or Claude Code) and the upstream Anthropic API. Rather than calling ``api.anthropic.com`` directly, all requests are routed through the gateway over TLS.

This architecture provides several benefits:

- **Centralised key management** — Your Anthropic API key is stored as a ``Secret`` in Smarter rather than in each developer's environment.
- **Auditability** — All prompt and completion traffic passes through a single controlled point.
- **Provider switching** — Changing the model or provider requires only a manifest update, not code changes.

When Claude Code is configured to use Smarter, three environment variables control routing:

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Variable
     - Purpose
   * - ``ANTHROPIC_BASE_URL``
     - Points Claude Code at the Smarter gateway instead of Anthropic directly
   * - ``ANTHROPIC_AUTH_TOKEN``
     - Your **Smarter** API key, used to authenticate with the gateway
   * - ``ANTHROPIC_API_KEY``
     - Must be explicitly empty; a value here causes Claude Code to bypass the gateway

.. _concept-manifests:

Manifests
~~~~~~~~~~

A **manifest** is a YAML file that declaratively describes a Smarter resource — such as a ``Secret``, a ``Provider``, or a ``ChatBot``. You apply manifests with the Smarter CLI (``smarter apply -f <file>.yml``), and Smarter reconciles the platform state to match the file's specification.

There are three manifest types relevant to this tutorial:

- **Secret manifest** — Stores your Anthropic API key securely. Smarter encrypts the value and exposes it to providers by reference, so the raw key never appears in your code or manifests.
- **Provider manifest** — Registers Claude as a named LLM provider, specifying the model (e.g., ``claude-code-1-0``), the base URL, and the linked secret.
- **ChatBot manifest** — Defines a deployable ChatBot resource that references the Claude provider, exposes an HTTP endpoint, and optionally configures system prompts and plugins.

.. _concept-provider-class:

The Provider Class
~~~~~~~~~~~~~~~~~~~

Within the Smarter codebase, each LLM provider is implemented as a Python class that subclasses ``OpenAICompatibleChatProvider``. This base class handles the OpenAI-compatible HTTP request/response format that Anthropic's API also supports.

The Claude provider class (``ClaudeChatProvider``) declares:

- The provider name (``"claude"``) used to look up the handler at runtime.
- The Anthropic base URL and the model to use by default.
- The API key, sourced from ``smarter_settings`` so it is never hard-coded.
- ``add_built_in_tools = False``, which disables tool injection that is not compatible with Claude models.

Once the class is registered in ``ChatProviders``, calling ``chat_providers.get_handler(provider="claude")`` resolves to ``ClaudeChatProvider.chat()``, which is the path taken every time a ChatBot backed by Claude processes a prompt.

.. _concept-secrets:

Secrets and API Key Security
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Smarter uses a **Secret** abstraction to store sensitive values such as API keys. A secret is created once — either via the CLI or a manifest — and is referenced by name elsewhere in your configuration. The raw value is encrypted at rest and never exposed in logs or manifests.

For Claude integration, you will create one secret that holds your Anthropic API key. The Provider manifest then references this secret rather than embedding the key directly. This separation means that rotating an API key requires updating only the secret, with no changes to any manifest or provider configuration.

.. warning::

   Never commit API keys to version control. Always use Smarter Secrets or environment variables,
   and add ``.env`` and ``config.yaml`` files to ``.gitignore``.

.. _concept-chatbot:

ChatBots
~~~~~~~~~

A **ChatBot** in Smarter is a deployable resource that wraps an LLM provider behind an HTTP endpoint. Once applied and deployed, a ChatBot exposes a public or authenticated URL that your application (or the Smarter Sandbox) can send prompts to.

Each ChatBot manifest specifies:

- **defaultProvider** — The registered provider name (``"claude"`` in this tutorial).
- **defaultModel** — The specific model version (e.g., ``claude-code-1-0``).
- **System prompt** — Optional instructions prepended to every conversation.
- **Plugins** — Optional extensions that augment the ChatBot's capabilities.

The ChatBot is the end-to-end unit of deployment: it is what you test against in the Sandbox, embed in a web page, and call from ``curl`` or Postman to validate Claude responses.

.. _concept-cli:

The Smarter CLI
~~~~~~~~~~~~~~~~

The **Smarter CLI** (``smarter``) is a statically compiled Go binary that provides a verb-based interface for managing all Smarter resources. Key commands used in this tutorial are:

.. list-table::
   :widths: 40 60
   :header-rows: 1

   * - Command
     - Purpose
   * - ``smarter configure``
     - Stores your Smarter API key and account number locally
   * - ``smarter whoami``
     - Confirms the CLI is authenticated against the platform
   * - ``smarter apply -f <file>.yml``
     - Creates or updates the resource described in a manifest
   * - ``smarter get providers``
     - Lists all registered LLM providers
   * - ``smarter get chatbots``
     - Lists all deployed ChatBots
   * - ``smarter describe chatbot <name>``
     - Shows detailed status and configuration for a ChatBot

The CLI communicates with the Smarter platform API using the credentials stored in ``$HOME/.smarter/config.yaml``. All manifest operations are idempotent — running ``smarter apply`` on an existing resource updates it rather than creating a duplicate.



Step-by-Step guide
--------------------------

Overview
~~~~~~~~~~~~~~~~~~~~~~~~~

This section describes how to integrate the Anthropic Claude provider into the Smarter platform.
and covers package creation, provider registration, seed data, environment configuration, and testing.


Step 1: Add a New Provider Package
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create the following files

.. code-block:: text

   smarter/apps/prompt/providers/claude/__init__.py
   smarter/apps/prompt/providers/claude/const.py
   smarter/apps/prompt/providers/claude/classes.py

Constants (``const.py``)
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # smarter/apps/prompt/providers/claude/const.py

   BASE_URL = "https://api.anthropic.com/v1/"
   PROVIDER_NAME = "claude"
   DEFAULT_MODEL = "claude-code-1-0"

Provider Class (``classes.py``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Subclass ``OpenAICompatibleChatProvider`` exactly as shown below:

.. code-block:: python

   # smarter/apps/prompt/providers/claude/classes.py

   from smarter.apps.provider.services.text_completion.base import OpenAICompatibleChatProvider
   from smarter.apps.provider.services.text_completion.claude.const import (
       BASE_URL,
       DEFAULT_MODEL,
       PROVIDER_NAME,
       VALID_CHAT_COMPLETION_MODELS,
   )
   from smarter.settings import smarter_settings


   class ClaudeChatProvider(OpenAICompatibleChatProvider):
       provider = PROVIDER_NAME
       base_url = BASE_URL
       api_key = smarter_settings.anthropic_api_key.get_secret_value()
       default_model = DEFAULT_MODEL
       default_system_role = smarter_settings.llm_default_system_role
       default_temperature = smarter_settings.llm_default_temperature
       default_max_tokens = smarter_settings.llm_default_max_tokens
       valid_chat_completion_models = VALID_CHAT_COMPLETION_MODELS
       add_built_in_tools = False

.. important::

   Set ``add_built_in_tools = False`` to match the expected behaviour for Claude models.

Step 2: Register the Provider in ``ChatProviders``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Edit ``smarter/apps/prompt/providers/providers.py``:

1. Import the new provider class and constant:

   .. code-block:: python

      from smarter.apps.provider.services.text_completion.claude.classes import ClaudeChatProvider
      from smarter.apps.provider.services.text_completion.claude.const import PROVIDER_NAME as CLAUDE_PROVIDER_NAME

2. Add a ``_claude`` instance attribute and a ``claude`` property:

   .. code-block:: python

      @property
      def claude(self) -> ClaudeChatProvider:
          if not hasattr(self, "_claude"):
              self._claude = ClaudeChatProvider()
          return self._claude

3. Add a handler method:

   .. code-block:: python

      def claude_handler(self, *args, **kwargs):
          return self.claude.chat(*args, **kwargs)

4. Register in ``all_handlers``:

   .. code-block:: python

      all_handlers = {
          # ... existing handlers ...
          "claude": claude_handler,
      }

5. Include in ``all`` (provider enumeration):

   .. code-block:: python

      all = [
          # ... existing providers ...
          self.claude.provider or "Claude",
      ]

.. note::

   This enables ``chat_providers.get_handler(provider="claude")`` to resolve correctly,
   which is required when a ``ChatBot`` is configured with ``provider="claude"``.

Step 3: Add Seed Provider Registration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Edit ``smarter/apps/provider/management/commands/initialize_providers.py``.

Constants
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   ANTHROPIC_API = "Anthropic"          # or "Claude" — must match DB display name
   ANTHROPIC_DEFAULT_MODEL = "claude-code-1-0"
   ANTHROPIC_API_KEY_NAME = "anthropic_api_key"

Initializer Method
^^^^^^^^^^^^^^^^^^^

Add ``initialize_anthropic()`` (or ``initialize_claude()``):

.. code-block:: python

   def initialize_anthropic(self):
       secret = Secret.objects.create(
           value=smarter_settings.anthropic_api_key.get_secret_value()
       )
       Provider.objects.get_or_create(
           name=ANTHROPIC_API,
           defaults=dict(
               base_url="https://api.anthropic.com/v1/",
               api_key=secret,
               connectivity_test_path="chat/completions",
               status=ProviderStatus.VERIFIED,
               is_active=True,
           ),
       )
       self.initialize_provider_models(provider_name=ANTHROPIC_API)

Registration
^^^^^^^^^^^^^^^^^^^^

Call the method inside ``handle()``:

.. code-block:: python

   def handle(self, *args, **options):
       # ... existing initializers ...
       self.initialize_anthropic()

.. tip::

   This seeds the platform provider metadata that Smarter uses to manage built-in providers.

Step 4: Validate Provider Name Support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``ChatBot.provider`` is validated via ``validate_provider()``, which checks membership
in ``chat_providers.all``. Registering the handler in Step 2 is sufficient for ``claude``
to pass validation automatically.

Additionally confirm:

- ``smarter/apps/chatbot/models.py`` — ``validate_provider()`` permits ``"claude"``
  (no manual changes required if ``all`` is updated correctly).
- Any manifest docs or examples that enumerate provider names include ``"claude"``.


Step 5: Add Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``smarter/apps/prompt/tests/test_claude_provider.py``:

.. code-block:: python

   import pytest
   from smarter.apps.provider.services.text_completion.providers import chat_providers


   def test_claude_provider_exists():
       """Verify the claude provider is registered."""
       assert hasattr(chat_providers, "claude")


   def test_claude_handler_callable():
       """Verify get_handler returns a callable for provider='claude'."""
       handler = chat_providers.get_handler("claude")
       assert callable(handler)


   def test_claude_handler_missing_api_key(monkeypatch):
       """Verify a meaningful error is raised when the API key is absent."""
       monkeypatch.setattr(
           chat_providers.claude, "api_key", ""
       )
       with pytest.raises(Exception, match="api_key"):
           chat_providers.get_handler("claude")()


   def test_claude_invalid_request():
       """Verify meaningful error on invalid request payload."""
       with pytest.raises(Exception):
           chat_providers.claude.chat(messages=[])

Optionally, add provider initialization tests in ``smarter/apps/provider/tests/``:

.. code-block:: python

   def test_initialize_anthropic_creates_provider():
       from smarter.apps.provider.models import Provider
       # Run initializer and verify DB record
       assert Provider.objects.filter(name="Anthropic").exists()

----

Step 6: Update Environment Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Requirement Variable
^^^^^^^^^^^^^^^^^^^^^^^

Add the required environment variable ``.env``:

.. code-block:: bash

   # Anthropic / Claude provider
   SMARTER_ANTHROPIC_API_KEY=your-anthropic-api-key-here

.. note::

   If you wish to support a ``SMARTER_CLAUDE_API_KEY`` alias, add an alias resolver
   in ``smarter_settings`` and document both names here.

Documentation
^^^^^^^^^^^^^^^^^^^^^^^

Update platform docs (e.g. ``docs/providers.rst`` or ``README.md``) with:

- Claude provider registration instructions.
- Example ``ChatBot`` manifest entries using ``provider: "claude"``.

Step 7 (Optional): Add a Provider Manifest Entry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If Smarter uses provider manifests for platform management, add Anthropic / Claude metadata in:

.. code-block:: text

   smarter/apps/provider/manifest/
   # or
   smarter/apps/provider/README.md

Naming Conventions
^^^^^^^^^^^^^^^^^^^^^^^

Use the following names consistently across the codebase:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Context
     - Value
   * - Internal provider key
     - ``claude``
   * - Supported model names
     - ``claude-code-1-0``
   * - Settings config key
     - ``smarter_settings.anthropic_api_key``
   * - Environment variable
     - ``SMARTER_ANTHROPIC_API_KEY``
   * - Database display name
     - ``Anthropic`` (or ``Claude``)

Summary of Files to Change
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 60 40

   * - File
     - Action
   * - ``smarter/apps/prompt/providers/claude/__init__.py``
     - Create (empty)
   * - ``smarter/apps/prompt/providers/claude/const.py``
     - Create
   * - ``smarter/apps/prompt/providers/claude/classes.py``
     - Create
   * - ``smarter/apps/prompt/providers/providers.py``
     - Edit
   * - ``smarter/apps/provider/management/commands/initialize_providers.py``
     - Edit
   * - ``.env.example``
     - Edit
   * - ``smarter/apps/prompt/tests/test_claude_provider.py``
     - Create
   * - ``smarter/apps/provider/tests/`` (optional)
     - Create / Edit

Verification
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Run provider initialization
"""""""""""""""""""""""""""""""

.. code-block:: bash

   python manage.py initialize_providers

Then confirm the new ``Anthropic`` provider record is created in the database.

Test the chat endpoint
"""""""""""""""""""""""""""""""

Deploy or call the chat endpoint with a ``ChatBot`` configured for ``provider="claude"``.

Run the test suite
"""""""""""""""""""""""""""""""

.. code-block:: bash

   pytest smarter/apps/prompt/tests
   pytest smarter/apps/provider/tests


Proof of Concept: Claude Code on Smarter
-----------------------------------------

Deploy a publicly accessible **Claude-backed ChatBot** on **Smarter** and confirm it returns a real completion response to a ``curl`` request.

.. _poc-expected-result:

Expected Result
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is what success looks like.

**Your deployed ChatBot URL:**

.. code-block:: text

   https://napl-claude-poc.3141.api.smarter.sh/

**Your** ``curl`` **test command:**

.. code-block:: bash

   curl -s -X POST \
     https://napl-claude-poc.3141.api.smarter.sh/chat/ \
     -H "Content-Type: application/json" \
     -d '{\"messages\": [{\"role\": \"user\", \"content\": \"Explain recursion in one sentence.\"}]}'

**The response you will receive:**

.. code-block:: json

   {
     "data": {
       "statusCode": 200,
       "body": {
         "id": "msg_01XqP...",
         "choices": [{
           "finish_reason": "stop",
           "index": 0,
           "message": {
             "role": "assistant",
             "content": "Recursion is when a function calls itself with
                         a simpler version of the original problem until
                         it reaches a base case that stops the repetition."
           }
         }],
         "model": "claude-code-1-0",
         "usage": {
           "prompt_tokens": 38,
           "completion_tokens": 29,
           "total_tokens": 67
         }
       }
     },
     "api": "smarter.sh/v1",
     "thing": "Chatbot",
     "metadata": { "command": "chat" }
   }

.. important::

   A ``statusCode`` of ``200`` and a non-empty ``choices[0].message.content``
   means the PoC is complete and Claude Code is fully operational on Smarter.

.. _poc-verification:

Verification
^^^^^^^^^^^^^^^^^^^^^^

Once your ChatBot is deployed (see the Step-by-Step section of this tutorial), run the following to confirm everything is working end-to-end.

Retrieve your exact ChatBot URL:

.. code-block:: bash

   smarter describe chatbot napl-claude-poc   # look for: url_chatbot

Or inspect the live config directly:

.. code-block:: text

   https://platform.smarter.sh/chatbots/napl-claude-poc/config/

Then run the ``curl`` command from the :ref:`Expected Result <poc-expected-result>`
section above, substituting your account number.

.. note::

   You can also verify end-to-end pipeline health in the Smarter Sandbox.
   Open the web console, send a prompt to ``napl-claude-poc``, and confirm
   a coherent Claude reply is returned through all five processing stages.


.. _poc-steps:

Steps
~~~~~
**1 — Configure the CLI**

.. code-block:: bash

   smarter configure   # enter your Smarter API key and account number
   smarter whoami      # confirm authentication

**2 — Set your Anthropic API key**

.. code-block:: bash

   export ANTHROPIC_API_KEY="sk-ant-..."   # Linux / macOS

.. code-block:: powershell

   setx ANTHROPIC_API_KEY "sk-ant-..."     # Windows PowerShell

.. warning::

   Never commit API keys to version control.

**3 — Create the ChatBot manifest**

.. code-block:: bash

   mkdir smarter-poc && cd smarter-poc
   smarter manifest chatbot -o yaml > napl-claude-poc.yml

Edit ``napl-claude-poc.yml`` with the following key fields:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: ChatBot
   metadata:
     name: napl-claude-poc
     namespace: default
   spec:
     defaultModel: claude-sonnet-4-6
     defaultProvider: anthropic
     appName: "NAPL Claude PoC"
     appDescription: "Proof-of-concept ChatBot backed by Claude on Smarter."
     appExamplePrompts:
       - "Explain recursion in one sentence."
       - "What is a transformer model?"
       - "Summarise the concept of zero-trust security."
     # plugins:   <-- omit for this PoC

**4 — Deploy**

.. code-block:: bash

   smarter apply -f napl-claude-poc.yml
   smarter describe chatbot napl-claude-poc   # confirm status: deployed

**5 — Run the** ``curl`` **test**

Replace ``<YOUR_ACCOUNT_NUMBER>`` with your account number, then run the
command from the :ref:`Expected Result <poc-expected-result>` section above.
Retrieve your exact ChatBot URL at any time with:

.. code-block:: bash

   smarter describe chatbot napl-claude-poc   # look for: url_chatbot

**6 — Confirm in the Smarter Sandbox**

Open the Smarter web console Sandbox and send a prompt to ``napl-claude-poc``.
A clean five-stage processing run — ending with a coherent Claude reply in
stage 5 — confirms the full pipeline is healthy.

.. _poc-definition-of-done:

Definition of Done
~~~~~~~~~~~~~~~~~~~~~~~~~

The PoC is complete when all four criteria are met:

.. raw:: html

   <table style="width:100%">
     <tbody>
       <tr><td style="vertical-align:middle; width:3%"><input type="checkbox"></td><td><code>smarter describe chatbot napl-claude-poc</code> returns <code>status: deployed</code></td></tr>
       <tr><td style="vertical-align:middle"><input type="checkbox"></td><td>The <code>curl</code> POST to <code>/chat/</code> returns <code>statusCode: 200</code></td></tr>
       <tr><td style="vertical-align:middle"><input type="checkbox"></td><td>The response body contains a non-empty <code>choices[0].message.content</code></td></tr>
       <tr><td style="vertical-align:middle"><input type="checkbox"></td><td>The Smarter Sandbox shows a complete 5-stage processing run</td></tr>
     </tbody>
   </table>
   <br>

.. important::

   Save the ``curl`` response as your PoC artefact for stakeholder review.


.. _troubleshooting-claude-code-in-smarter:


Troubleshooting Claude Code in Smarter
-----------------------------------------

Common pitfalls and fixes for integrating **Claude Code** with the **Smarter** platform.

.. note::

   Infrastructure provisioning, IDE integration, and cost tracking are out of scope.
   See :ref:`escalation-path` for the correct contacts.

.. _quick-diagnosis-reference:

Quick Diagnosis Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 40 35 25
   :header-rows: 1

   * - Symptom
     - Probable Cause
     - See Section
   * - ``command not found: claude``
     - Not installed or PATH not set
     - :ref:`ts-01-gateway-connection`
   * - ``401 Unauthorized`` / ``Invalid API key``
     - Missing or misconfigured key
     - :ref:`ts-02-api-key-issues`
   * - ``smarter apply`` fails silently
     - YAML error or missing required fields
     - :ref:`ts-03-manifest-apply-errors`
   * - Slow responses / ``Context window exceeded``
     - Token bloat or wrong working directory
     - :ref:`ts-04-context-performance`
   * - Sandbox shows stale behaviour
     - Cached config or manifest not re-applied
     - :ref:`ts-05-sandbox-config`
   * - Chatbot widget missing on web page
     - Wrong API URL or missing CDN script
     - :ref:`ts-06-web-integration`

.. _ts-01-gateway-connection:

TS-01 — Gateway Connection Failures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms:** Claude Code bypasses Smarter, ignores ``ANTHROPIC_BASE_URL``,
or returns a connection error.

**Shell profile not sourced** — After editing ``~/.zshrc``, run:

.. code-block:: bash

   source ~/.zshrc

**Incorrect environment variables** — All three variables below are required:
See :ref:`ts-02-api-key-issues` for the correct value for each variable.

.. code-block:: bash

   export ANTHROPIC_BASE_URL="https://<your-smarter-gateway-endpoint>"
   export ANTHROPIC_AUTH_TOKEN="YOUR_SMARTER_API_KEY"
   export ANTHROPIC_API_KEY=""   # must be empty

.. warning::

   If ``ANTHROPIC_API_KEY`` contains a value, Claude Code will bypass
   the Smarter gateway and call Anthropic directly.

**Windows (PowerShell)**

.. code-block:: powershell

   $env:ANTHROPIC_BASE_URL   = "https://<your-smarter-gateway-endpoint>"
   $env:ANTHROPIC_AUTH_TOKEN = "YOUR_SMARTER_API_KEY"
   $env:ANTHROPIC_API_KEY    = ""

**Gateway unreachable** — Confirm the endpoint is live:

.. code-block:: bash

   curl -I https://<your-smarter-gateway-endpoint>/v1/messages

A ``400 Bad Request`` response indicates missing ``anthropic-beta`` or
``anthropic-version`` headers — escalate to the infrastructure team.

.. _ts-02-api-key-issues:

TS-02 — API Key Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms:** ``401 Unauthorized``, ``403 Forbidden``, or
``smarter: authentication error``.

Re-run the interactive configuration to reset stored credentials:

.. code-block:: bash

   smarter configure
   smarter whoami   # confirm authentication

.. list-table::
   :widths: 40 60
   :header-rows: 1

   * - Variable
     - Value
   * - ``ANTHROPIC_BASE_URL``
     - Your Smarter gateway endpoint URL
   * - ``ANTHROPIC_AUTH_TOKEN``
     - Your **Smarter** API key
   * - ``ANTHROPIC_API_KEY``
     - Must be explicitly empty (``""``)

.. warning::

   Do not confuse your **Smarter API key** with your **Anthropic API key**.
   When routing Claude Code through Smarter, the Smarter key belongs in
   ``ANTHROPIC_AUTH_TOKEN``. If ``ANTHROPIC_API_KEY`` contains any value,
   Claude Code bypasses the Smarter gateway and calls Anthropic directly.

.. note::

   Paste API keys into a plain-text editor first to strip invisible
   whitespace before applying. Contact your administrator if you
   need key scopes verified.

.. _ts-03-manifest-apply-errors:

TS-03 — Manifest Apply Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms:** ``smarter apply`` errors out, exits silently, or deploys
with unexpected settings.

**Validate YAML before applying:**

.. code-block:: bash

   python3 -c "import yaml; yaml.safe_load(open('my-chatbot.yml'))" \
           && echo "YAML is valid"

**Generate a reference template to compare against your file:**

.. code-block:: bash

   smarter manifest chatbot -o yaml > reference-chatbot.yml

**List valid provider names** — ``defaultProvider`` must match exactly:

.. code-block:: bash

   smarter get providers

**Reset a misconfigured chatbot** — ``apply`` does not remove fields
absent from your manifest. Delete and re-create for a clean state:

.. code-block:: bash

   smarter delete chatbot <name>
   smarter apply -f my-chatbot.yml

.. important::

   Confirm deployment before moving on:

   .. code-block:: bash

      smarter get chatbots
      smarter describe chatbot <your-chatbot-name>

.. _ts-04-context-performance:

TS-04 — Context and Performance Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms:** Slow responses, irrelevant suggestions, unsaved edits,
or token quota warnings.

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - In-Session Command
     - Effect
   * - ``/clear``
     - Resets conversation context entirely
   * - ``/compact``
     - Summarises and compresses the current session
   * - ``/config``
     - Opens the Claude Code configuration panel

**Wrong working directory** — Always launch Claude Code from the project root:

.. code-block:: bash

   cd /path/to/your/project && claude

**Read-only file permissions** — If edits are not saving:

.. code-block:: bash

   ls -la && chmod 644 <filename>

.. note::

   Every entry in ``spec.functions`` is injected into every prompt,
   increasing token cost. Remove unused functions during development.
   Add a ``CLAUDE.md`` file to improve suggestion relevance.

.. _ts-05-sandbox-config:

TS-05 — Sandbox Reflects Stale Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms:** Wrong model, outdated behaviour, or plugins not triggering
in the Smarter Sandbox.

- **Force a browser cache clear:** ``Cmd+Shift+R`` (macOS) or ``Ctrl+Shift+R`` (Windows/Linux)
- **Re-apply the manifest** after any local file change: ``smarter apply -f my-chatbot.yml``
- **Remove unconfigured plugins** — an empty ``plugins:`` block causes silent failures; comment it out during initial testing
- **Inspect the live config** directly:

.. code-block:: text

   https://platform.smarter.sh/chatbots/<your-chatbot-name>/config/

.. _ts-06-web-integration:

TS-06 — Web Integration and Embedding Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


**Symptoms:** Chatbot widget missing, blank, or broken on the web page.

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Chatbot Type
     - URL Pattern
   * - Public (deployed)
     - ``https://<chatbot-name>.<account-id>.api.smarter.sh/``
   * - Authenticated
     - ``https://platform.smarter.sh/chatbots/<chatbot-name>/``

**CDN loader script** — must be present in ``<head>``:

.. code-block:: html

   <script src="https://cdn.platform.smarter.sh/ui-chat/app-loader.js"></script>

**React root element** — must exist in the DOM before the script loads:

.. code-block:: html

   <div id="root"
        smarter-chatbot-api-url="https://<chatbot-name>.<account-id>.api.smarter.sh/">
   </div>

**Chatbot not yet deployed** — verify status before embedding a public URL:

.. code-block:: bash

   smarter describe chatbot <name>   # confirm status: deployed

.. _escalation-path:

Escalation Path
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 55 45
   :header-rows: 1

   * - Issue Type
     - Contact
   * - Platform unreachable / gateway down
     - **Infrastructure Team** *(out of scope)*
   * - IDE not recognising ``claude`` command
     - **IDE Integration Team** *(out of scope)*
   * - Token budget or cost code questions
     - **Accounting / FinOps Team** *(out of scope)*
   * - Smarter API key provisioning
     - Smarter Account Administrator
   * - Claude Code bugs or unexpected AI behaviour
     - Anthropic Support — ``support.anthropic.com``
   * - Manifest and deployment questions
     - ``docs.smarter.sh``
