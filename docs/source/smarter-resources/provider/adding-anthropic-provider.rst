How-To: Add an Anthropic Provider for Claude Code Workflows
===========================================================

Goal
----

This tutorial shows how to register **Anthropic** as an upstream LLM provider in Smarter.

Once registered, this provider can serve as the platform foundation for Claude Code-related
workflows in Smarter.


Prerequisites
-------------

- Administrative access to Smarter
- The ``smarter`` CLI installed (:doc:`/smarter-framework/smarter-cli`)
- An Anthropic API key

Setup
-----

Make sure the Anthropic API key is available to Smarter before applying the provider
manifest. In many Smarter deployments, this is configured in the ``.env`` file.

.. warning::

   Never commit a real Anthropic API key to Git.

Concept Overview
----------------

A ``Provider`` resource defines an upstream LLM provider that other
Smarter resources can use.

In this tutorial, Smarter is the internal platform and Anthropic is the
external provider. The manifest tells Smarter how to identify Anthropic
and how to attempt a connection to its API.

A provider manifest in this repo uses the usual Smarter manifest layout:

- ``apiVersion`` for the manifest version
- ``kind`` set to ``Provider``
- ``metadata`` for the resource name and description
- ``spec.provider`` for the provider connection details

After you apply the manifest, Smarter registers the provider and begins
verification using the values in ``spec.provider``.

.. note::

   ``ProviderModel`` exists in the runtime data model, but this repository
   does not show a supported ``smarter apply`` manifest path for
   ``kind: ProviderModel``. This page covers provider registration only.

Step-by-Step
------------

Step 1: Generate a starting template
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run:

.. code-block:: bash

   smarter manifest provider

This prints a valid example provider manifest. Use it as the reference
for the YAML structure.

Step 2: Create the Anthropic provider manifest
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a file named ``anthropic-provider.yaml``.

The example below keeps the same ``spec.provider`` nesting shown by
``smarter manifest provider`` and uses only the fields needed for this
tutorial.

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: Anthropic
     description: Anthropic provider for Claude family models
     version: 1.0.0
   spec:
     provider:
       name: Anthropic
       description: Anthropic provider for Claude family models
       base_url: https://api.anthropic.com
       api_key: anthropic-api-key
       connectivity_test_path: /v1/models

Supported optional fields in the built-in example include ``tags``,
``annotations``, ``logo``, ``website_url``, ``contact_email``,
``support_email``, ``terms_of_service_url``, ``docs_url``, and
``privacy_policy_url``. They are supported, but not required for a short
Anthropic example.

.. note::

   Keep ``metadata.name`` and ``spec.provider.name`` identical. The
   broker uses the metadata name for lookup, while the nested provider
   spec is what gets stored on the provider record.

Step 3: Apply the manifest
~~~~~~~~~~~~~~~~~~~~~~~~~~

Run:

.. code-block:: bash

   smarter apply -f anthropic-provider.yaml

Step 4: Verify the provider
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run:

.. code-block:: bash

   smarter get providers
   smarter describe provider Anthropic

Proof of Concept
----------------

The tutorial is successful when:

- ``Anthropic`` appears in ``smarter get providers``
- ``smarter describe provider Anthropic`` shows ``is_verified: true``
- the provider is ready to be referenced by downstream Smarter resources

An example of the kind of status you are looking for is:

.. code-block:: yaml

   status:
     is_active: true
     is_verified: true

Troubleshooting
---------------

Invalid or missing API key
~~~~~~~~~~~~~~~~~~~~~~~~~~

Check that the Anthropic API key is available to Smarter.

Provider stuck in verifying state
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Wait briefly and run:

.. code-block:: bash

   smarter describe provider Anthropic

If the status does not change, check the provider configuration again.

Incorrect base URL or connectivity path
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check ``base_url`` and ``connectivity_test_path`` in the manifest.

Manifest formatting problems
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run ``smarter manifest provider`` again and compare the structure.

See Also
--------

- :doc:`Smarter Provider <../smarter-provider>`
- :doc:`Provider Verification <verification>`
- `Anthropic Documentation <https://docs.anthropic.com/>`__
