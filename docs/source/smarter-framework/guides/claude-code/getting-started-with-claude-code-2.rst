How-To: Add Anthropic as an LLM Provider in Smarter
===================================================

Goal
----

This tutorial shows how to add Anthropic as an LLM provider in Smarter using a provider manifest.

In this example, Anthropic is used because Claude Code is the intended downstream use case.

Prerequisites
-------------

This tutorial assumes you already have:

- Administrative access to the Smarter environment
- The Smarter CLI installed and available
- Permission to apply manifests
- An Anthropic API key
- Basic familiarity with YAML and command-line tools

Setup
-----

Before creating the provider manifest, make sure the Anthropic API key is available to Smarter as a secret or environment-level configuration.

See Anthropic's documentation at `Get started with Claude <https://platform.claude.com/docs/en/get-started>`__ for current information.

Concept Overview
----------------

In Smarter, a ``Provider`` resource defines an upstream LLM provider that other Smarter resources can use.

For this tutorial:

- Smarter acts as the internal platform
- Anthropic is the upstream provider
- Claude is the model family
- The provider manifest defines how Smarter connects to Anthropic

Step-by-Step
------------

Step 1: Generate a starting template
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run:

.. code-block:: bash

   smarter manifest provider

Step 2: Create the provider manifest
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a file named ``anthropic-provider.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic_provider
     description: Anthropic provider for Claude models
     version: 1.0.0
   spec:
     provider:
       name: Anthropic
       description: Anthropic API provider
       base_url: https://api.anthropic.com/v1
       api_key: anthropic_api_key
       connectivity_test_path: /models

Step 3: Apply the manifest
~~~~~~~~~~~~~~~~~~~~~~~~~~

Run:

.. code-block:: bash

   smarter apply -f anthropic-provider.yaml

Step 4: Verify the provider
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run:

.. code-block:: bash

   smarter describe provider anthropic_provider

Proof of Concept
----------------

A successful result is a provider resource that is active and available for later chatbot or agent configuration.

Troubleshooting
---------------

Provider does not apply
~~~~~~~~~~~~~~~~~~~~~~~

Check the YAML formatting and required fields.

Provider does not verify
~~~~~~~~~~~~~~~~~~~~~~~~

Check that the Anthropic API key is available to Smarter and that the base URL and connectivity test path are correct.

Optional Next Step
------------------

After the provider is active, the next logical step would be to create a chatbot that uses it.

The following example shows the intended shape of an Anthropic chatbot manifest, based on the same style as the ``smarter-deploy`` OpenAI chatbot example. This is shown as a target-state example only.

.. note::

   In the current Smarter repo, chatbot providers appear to be limited to OpenAI, Google AI, and Meta AI. Additional implementation would likely be required before an Anthropic chatbot could work end-to-end.

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Chatbot
   metadata:
     description: "An Anthropic Claude pass-through chatbot."
     name: anthropic_claude
     version: 0.1.0
   spec:
     apiKey: null
     config:
       appAssistant: Claude
       appBackgroundImageUrl: null
       appExamplePrompts:
         - Write a Python function that generates the Fibonacci sequence.
         - Summarize a technical document in 100 words or less.
         - Provide a technical definition for the term "machine learning."
       appFileAttachment: false
       appInfoUrl: https://www.anthropic.com/
       appLogoUrl: https://platform.smarter.sh/static/images/logo/smarter-crop.png
       appName: Anthropic Claude
       appPlaceholder: Ask me anything...
       appWelcomeMessage: Welcome to Claude!
       customDomain: null
       defaultMaxTokens: 4096
       defaultModel: claude-3-5-sonnet
       defaultSystemRole: You are a helpful chatbot.
       defaultTemperature: 0.5
       deployed: true
       provider: anthropic
       subdomain: null
     functions: []
     plugins: []

This step is outside the main scope of this tutorial. The main objective here is adding the provider itself.
