
================================
How-To: Adding Anthropic to Smarter
================================

Goal
====

Northern Aurora Power & Light (NAPL) wants its programmers
to use Claude Code with Smarter.

Before we can do that, Smarter needs access to Anthropic,
the company that provides the Claude AI models.

This guide explains how to check whether Anthropic is
already available and how to add it if needed.

Prerequisites
=============

Before starting, you will need:

- Access to a running Smarter installation.
- An administrator account if you need to add a provider.
- The Smarter command-line tool if you are adding a provider.
- An Anthropic API key if one has not already been configured.

If your company already provides Anthropic through Smarter,
you may not need to configure anything yourself.


Setup
=====

First, check if Anthropic is already available.

1. Log in to Smarter.
2. Select Providers from the left menu.
3. Check Your Providers and Shared Providers.
4. Look for a provider named ``anthropic``.

If Anthropic is already listed and available, you can
skip the provider setup. Ask your administrator to confirm
that your account has permission to use it.

If Anthropic is not available, an administrator will need
to configure it.

The administrator will need an Anthropic API key from
https://console.anthropic.com/.

For a self-hosted Smarter installation, add the key to
the deployment's ``.env`` file:

.. code-block:: bash

   SMARTER_ANTHROPIC_API_KEY=your-api-key-here

Restart Smarter to load the new setting:

.. code-block:: bash

   make restart

Never put a real API key in a tutorial, Git repository,
or other shared document.


Concept Overview
================

Smarter uses configuration files called manifests to
register AI providers.

A manifest is simply a YAML text file that tells Smarter
which provider and AI model you want to use.

In our case:

- Anthropic is the provider.
- Claude is the AI model.
- Claude Code is the programming assistant that uses Claude.

Adding Anthropic does not automatically install or
configure Claude Code. We will cover that separately.

Step-by-Step: Register Anthropic
================================

1. Generate a sample Provider manifest:

   .. code-block:: bash

      smarter manifest provider

2. Use the sample as a guide to create a file named
   ``anthropic-napl.yaml``.

   .. code-block:: yaml

      apiVersion: smarter.sh/v1
      kind: Provider
      metadata:
        name: anthropic-napl
        description: Anthropic provider for NAPL programmers
        version: 1.0.0
      spec:
        provider:
          name: anthropic
          model: claude-sonnet-4-6

3. Register the provider with Smarter:

   .. code-block:: bash

      smarter apply -f anthropic-napl.yaml

4. Check the provider's status:

   .. code-block:: bash

      smarter describe provider anthropic-napl

   Check the status information to see whether
   Smarter has verified the provider.

If your company already has a working Anthropic provider,
you do not need to create another one.


Proof of Concept
================

Now we need to confirm that Smarter recognizes Anthropic.

1. Log in to Smarter.
2. Open Providers from the left menu.
3. Find ``anthropic`` under Shared Providers or
   ``anthropic-napl`` under Your Providers.
4. Check that the provider is available.

If you registered a new provider, you can also check
its status using:

.. code-block:: bash

   smarter describe provider anthropic-napl

A successful verification confirms that Smarter can
communicate with the provider.

This does not mean Claude Code is working yet.
That is the next part of our project.

Troubleshooting
===============

**Anthropic is not listed**

Check that the provider was registered successfully.
If your company manages shared providers, contact
your Smarter administrator.

**API key not found**

Make sure the administrator added the Anthropic API
key to the correct ``.env`` file and restarted Smarter.

**Provider verification failed**

Check that the API key is valid and that the selected
Claude model is available to your Anthropic account.

**Manifest errors**

Check the YAML file for spelling and indentation errors.
YAML is sensitive to spaces.

**Permission denied**

Your account may not have permission to create or use
the provider. Contact your Smarter administrator.

References
==========

- :doc:`/smarter-platform/adding-an-llm-provider`
- :doc:`/smarter-resources/smarter-provider`
- `Anthropic documentation <https://docs.anthropic.com/>`_

