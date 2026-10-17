.. _getting-started-llm-provider:

Getting Started: Using an LLM Provider with Smarter
===================================================

Goal
----

Add an LLM provider to Smarter, verify its connection, and make one of its
models available to an LLMClient. The examples use generic names: substitute
the endpoint, credential, and model identifier supplied by your provider.

Prerequisites
-------------

You should already have:

* A Smarter account and access to the target Smarter environment.
* The Smarter CLI installed and configured for that environment. See
  :doc:`the CLI guide <../smarter-cli>`.
* An API key for the LLM provider, or access to the deployment's approved
  credential-management process.
* Permission to apply provider resources and access the Smarter Workbench.
  Provider credentials and provider initialization may require assistance
  from a platform administrator.
* Familiarity with YAML, shell commands, and environment-variable-based
  configuration.

Setup
-----

Configure the Smarter CLI for the intended environment, then check the
connection and identity before changing resources:

.. code-block:: console

   smarter status
   smarter whoami

Obtain the provider's API key and API documentation, including its API base
URL and a path that can be used to check connectivity. Keep the API key out
of source control. A Smarter API key authenticates you to Smarter; the
provider API key authenticates Smarter to the model service.

Concept Overview
----------------

Provider onboarding has separate credential, connection, and model concerns:

* A **Secret** stores the provider API key in Smarter's encrypted credential
  store.
* A **Provider** records the service name, API base URL, Secret reference,
  and connectivity-check path.
* A **provider model** identifies a model exposed by that service. Registering
  a Provider does not necessarily discover or register its models.
* An **LLMClient** selects a registered provider and model and defines the
  behavior exposed to users in the Workbench.

Smarter has built-in integrations for supported providers. Their credentials
are configured on the Smarter deployment, and the platform administrator
runs ``initialize_providers`` to initialize the providers and discover their
models. See
:doc:`the provider onboarding reference </smarter-platform/adding-an-llm-provider>`
for the built-in provider list and corresponding environment variables.

For a provider configured as an account resource, apply a Secret and then a
Provider manifest. The API endpoint and authentication scheme must be
compatible with an integration supported by the Smarter deployment; adding a
Provider manifest alone does not implement a new model protocol.

Step-by-Step
------------

Step 1: Check whether the provider is already available
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

List the providers in your target environment:

.. code-block:: console

   smarter get providers

If your provider is already listed, inspect it and its models before
continuing:

.. code-block:: console

   smarter describe provider <provider-name> -o yaml
   smarter get providers <provider-name> models

Do not create a duplicate provider simply because it is not visible in your
personal resources. Provider ownership and sharing are managed by the
platform; ask your administrator if you cannot access an existing provider.

Step 2: Create a Secret for the API key
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For an account-managed provider, create a local manifest named
``provider-secret.yaml``. Replace the placeholder with the API key before
applying it:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Secret
   metadata:
     name: example_provider_api_key
     description: API key for the example LLM provider
     version: 1.0.0
   spec:
     config:
       value: <provider-api-key>

Apply the Secret:

.. code-block:: console

   smarter apply -f provider-secret.yaml

The manifest contains the plaintext credential before it is applied. Keep it
in an ignored local file, do not commit it, and remove it after applying. If
your organization requires a deployment secret manager instead, use that
process and do not put the key in a manifest.

Step 3: Create the Provider manifest
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``provider.yaml`` and replace the example values with the provider's
actual service details:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: example_provider
     description: Example LLM provider
     version: 1.0.0
   spec:
     provider:
       name: example_provider
       description: Example provider API
       base_url: https://api.provider.example/v1/
       api_key: example_provider_api_key
       connectivity_test_path: /models

The ``api_key`` field names the Smarter Secret created in the previous step;
it is not the raw API key. Use the endpoint and connectivity path documented
by your provider. The sample ``/models`` path is not universal. For the
complete Provider manifest schema, see
:doc:`the Provider manifest reference </smarter-resources/provider/manifest>`.

Apply the Provider:

.. code-block:: console

   smarter apply -f provider.yaml

Step 4: Verify the Provider
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Inspect the registered Provider:

.. code-block:: console

   smarter describe provider example_provider -o yaml

Check its status for successful connectivity verification. If the status is
pending, allow the platform's verification process to run, then describe the
Provider again. If verification fails, use the troubleshooting section below
to check the Secret, endpoint, path, and network access.

Step 5: Confirm a model is registered
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

List the models associated with the Provider:

.. code-block:: console

   smarter get providers example_provider models

If the list is empty, registering the Provider was not enough to make a model
available. Built-in integrations can discover models when the administrator
runs ``initialize_providers`` with the required provider credentials. For
other integrations, ask the provider administrator how models are registered
in your Smarter deployment. Use an exact model identifier supported by both
the provider account and the integration.

Step 6: Test a programming prompt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once the Provider and a model are available to your account, create a sandbox
LLMClient manifest named ``programming-smoke-test.yaml``. Replace
``<registered-model-name>`` with a model returned in the previous step:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: LLMClient
   metadata:
     name: programming_smoke_test
     description: Sandbox LLMClient for testing a provider
     version: 1.0.0
   spec:
     config:
       appName: Programming Smoke Test
       appAssistant: Assistant
       provider: example_provider
       defaultModel: <registered-model-name>
       defaultSystemRole: >
         You are a precise programming assistant. Return concise,
         executable Python code and focused pytest tests.
       deployed: false

Apply the manifest:

.. code-block:: console

   smarter apply -f programming-smoke-test.yaml

Open the Smarter Workbench, select **Programming Smoke Test**, and submit:

.. code-block:: text

   Write a Python function normalize_username(value: str) -> str that trims
   leading and trailing whitespace, lowercases the value, and replaces each
   run of whitespace characters with one underscore. Include three pytest
   tests for ordinary input, mixed case, and repeated whitespace. Show the
   implementation and tests; do not read or write project files.

.. _llm-provider-tutorial-proof:

Proof of Concept
----------------

The provider setup is successful when:

* ``smarter describe provider example_provider -o yaml`` shows successful
  connectivity verification.
* ``smarter get providers example_provider models`` lists the model selected
  in the LLMClient manifest.
* The sandbox LLMClient applies successfully and is available in the
  Workbench.
* The Workbench returns a Python implementation and tests covering the
  requested whitespace and case-normalization behavior.

These checks verify both that Smarter can reach the provider and that an
LLMClient can use a registered model. They do not install or configure a
provider's own command-line or IDE coding assistant.

Troubleshooting
---------------

**The Secret cannot be found**

Check that the Secret was applied successfully and that the Provider's
``api_key`` field exactly matches the Secret name. Confirm that the Secret
and Provider are available to the same account.

**Provider connectivity verification fails**

Confirm that ``base_url`` and ``connectivity_test_path`` match the provider's
documented API. Check that the Smarter application can reach that endpoint and
that the referenced Secret contains a valid, active key.

**The Provider is verified, but no models are listed**

Provider verification checks the connection; it does not guarantee that
models were discovered or registered. Check whether your provider is a
built-in integration, and ask the platform administrator to run the
documented initialization or model-registration workflow for the deployment.

**The model appears in the list but the LLMClient request fails**

Confirm the LLMClient's ``provider`` and ``defaultModel`` values match the
registered Provider and model identifiers exactly. The provider must also use
a model protocol supported by the Smarter deployment.

**The manifest is rejected**

Check YAML indentation, resource names, and required fields. Generate a
reference manifest with ``smarter manifest provider`` and compare its
structure with the
:doc:`Provider manifest reference </smarter-resources/provider/manifest>`.

For provider-specific onboarding details, see
:doc:`Adding an LLM Provider </smarter-platform/adding-an-llm-provider>`.
