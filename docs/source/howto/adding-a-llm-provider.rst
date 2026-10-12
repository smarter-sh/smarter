Add Anthropic Claude to Smarter
=========================================

Goal
----

We will use Claude Code with Smarter to register Anthropic as an LLM provider and make a Claude model available as a managed resource.

Prerequisites
-------------

* Smarter v0.11.0 or later
* Administrator-level account with access to the web console.
* Smarter CLI installed. See :doc:`/smarter-framework/smarter-cli`.
* A text editor. VS Code with the
  `Smarter YAML extension <https://marketplace.visualstudio.com/items?itemName=querium.smarter-manifest>`_
  is recommended.
* Obtaining an Anthropic API key and managing it securely.

Setup
-----

Before starting, ensure you have:

#. A working Smarter installation and authenticated CLI.
#. An Anthropic API key with access to the intended Claude model.
#. A secure way to make the API key available to Smarter.
#. A working directory in which to create YAML manifest files.

Verify your CLI installation:

.. code-block:: bash

   smarter version
   smarter whoami

Concept Overview
----------------

Smarter uses a provider manifest to describe how it connects to an upstream LLM service. 
The provider configuration identifies the service, API endpoint, credentials and the endpoint used for connectivity verification.

The key configuration data points are:

+-------------------------------+-----------------------------------------------+----------------------------------------------+
| Data point                    | Example                                       | Purpose                                      |
+===============================+===============================================+==============================================+
| ``apiVersion``                | ``smarter.sh/v1``                             | Identifies the manifest format.              |
+-------------------------------+-----------------------------------------------+----------------------------------------------+
| ``kind``                      | ``Provider``                                  | Identifies the resource being created.       |
+-------------------------------+-----------------------------------------------+----------------------------------------------+
| ``metadata.name``             | ``anthropic_provider``                        | Names the Smarter resource.                  |
+-------------------------------+-----------------------------------------------+----------------------------------------------+
| ``metadata.description``      | ``Anthropic provider for Claude models``      | Describes the resource.                      |
+-------------------------------+-----------------------------------------------+----------------------------------------------+
| ``metadata.version``          | ``1.0.0``                                      | Records the manifest version.                |
+-------------------------------+-----------------------------------------------+----------------------------------------------+
| ``spec.provider.name``        | ``Anthropic``                                 | Identifies the upstream provider.            |
+-------------------------------+-----------------------------------------------+----------------------------------------------+
| ``spec.provider.description`` | ``Anthropic API provider``                    | Describes the provider integration.           |
+-------------------------------+-----------------------------------------------+----------------------------------------------+
| ``spec.provider.base_url``    | ``https://api.anthropic.com/v1``               | Specifies the API endpoint.                  |
+-------------------------------+-----------------------------------------------+----------------------------------------------+
| ``spec.provider.api_key``     | ``anthropic_api_key``                         | References the configured credential.        |
+-------------------------------+-----------------------------------------------+----------------------------------------------+
| ``spec.provider.connectivity_test_path`` | ``/models``                         | Specifies the connectivity test endpoint.    |
+-------------------------------+-----------------------------------------------+----------------------------------------------+

**Important:** Claude Code is not the model identifier. Claude Code is the coding assistant; the model identifier must be a supported Anthropic model, such as ``claude-sonnet-4-6``, where available.

Step-by-Step
------------

Step 1: Add the Anthropic API key to Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
1. Sign in at `https://console.anthropic.com/ <https://console.anthropic.com/>`_.
2. Navigate to **Settings > API Keys > Create Key**.

.. figure:: /_static/api-key-claude.png
   :alt: Anthropic Console API Keys

   Anthropic Console API Keys

3. Give it a descriptive name (e.g. ``smarter-claudecode``) and copy the value
   immediately as it will not be shown again.

.. danger::

   Never commit API keys to version control.

Step 2: Add the Key to Smarter
--------------------------------

Open the ``.env`` file at the root of your Smarter deployment and add:

.. code-block:: bash

   SMARTER_ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

Restart the application to load the new credential:

.. code-block:: bash

   make restart


Step 3: Generate a Template
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the Smarter CLI command:

.. code-block:: bash

   smarter manifest provider

Step 4: Create the Provider Manifest
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a file named ``anthropic-provider.yaml`` with the following content:

.. code-block:: yaml

    apiVersion: smarter.sh/v1
    kind: Provider
    metadata:
        name: anthropic-sonnet
        description: Anthropic Claude Sonnet provider
        version: 1.0.0
    spec:
        provider:
            name: anthropic
            model: claude-sonnet-4-6


Step 5: Apply the Manifest
~~~~~~~~~~~~~~~~~~~~~~~~~~

From the directory containing the YAML file, run:

.. code-block:: bash

   smarter apply -f anthropic-provider.yaml

Smarter will process the manifest and attempt to create the provider resource.

Step 6: Verify the Provider
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run:

.. code-block:: bash

   smarter describe provider anthropic-sonnet

Review the resource details and verification status. If verification fails, resolve the reported issue before proceeding further.

Success Criteria
----------------

Items to confirm a successful provider registration include:

* The ``anthropic_provider`` resource exists in Smarter.
* The provider configuration points to the Anthropic API.
* The configured credential is available to Smarter.
* The provider passes the applicable connectivity and verification checks.

Troubleshooting
---------------

Manifest fails to apply
~~~~~~~~~~~~~~~~~~~~~~~

Check YAML indentation, field names, and required values. Compare your manifest against the template generated by your installed Smarter CLI.

Provider verification fails
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Confirm the API key, base URL, and connectivity test path. Ensure the Smarter environment can reach the Anthropic API.

Authentication fails
~~~~~~~~~~~~~~~~~~~~

Confirm the credential is valid, has the necessary access, and is available to the Smarter service.

API key not found
~~~~~~~~~~~~~~~~~

Check that SMARTER_ANTHROPIC_API_KEY is present in .env and restart Smarter.

Model not found
~~~~~~~~~~~~~~~

Check the exact model identifier, including spelling and case, and confirm that the model is available to your Anthropic account

Provider registers but Claude Code does not work
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check whether your Smarter version supports the required Anthropic model and client integration. Provider registration alone does not guarantee Claude Code compatibility.

Model is not recognized
~~~~~~~~~~~~~~~~~~~~~~~

Use a valid Anthropic model identifier rather than ``Claude Code`` as the model name. Confirm that the selected model is available to your Anthropic account and supported by your Smarter configuration.
