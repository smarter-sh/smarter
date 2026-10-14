====================================================
Getting Started with Claude Code and Smarter at NAPL
====================================================

.. contents:: Table of Contents
   :local:
   :depth: 2

This guide explains the complete workflow for using Claude Code through
Northern Aurora Power & Light's (NAPL) centrally managed Smarter platform.
It begins with the administrative setup required to make Anthropic available
in Smarter and then continues into programmer self-onboarding and a small
proof-of-concept coding workflow.


Goal
====

Configure Anthropic as an LLM provider in Smarter and then use Claude Code
through the NAPL Smarter environment to inspect an existing programming
project and complete a small developer task.

The intended end-to-end path is:

.. code-block:: text

   NAPL administrator
        |
        | configures Anthropic provider
        v
      Smarter
        |
        | provides centrally managed access
        v
   Programmer -> Claude Code -> Smarter -> Anthropic -> Claude model

The administrator manages the organization-level Anthropic provider
configuration and credential. Programmers authenticate to Smarter using
their own Smarter credentials and do not need access to the
organization-level Anthropic API key.


Prerequisites
=============

Before beginning, confirm that the following are available.

For the Smarter administrator:

* Administrator access to the NAPL Smarter platform.
* The Smarter CLI installed and configured for the correct environment.
* An Anthropic API credential approved for organizational use.
* Permission to manage provider credentials and LLM provider configuration.
* Basic familiarity with YAML and command-line tools.

For the programmer:

* An active NAPL Smarter account and the ability to log in.
* Command-line proficiency on the workstation operating system.
* Familiarity with environment variables, JSON, Git, and normal development
  workflows.
* A local programming project that can safely be used for an onboarding test.
* Network access to the NAPL Smarter environment.
* A personal Smarter API credential, or access to the NAPL-approved process
  for obtaining one.

.. warning::

   Do not place a real Anthropic API key or personal Smarter API key in a Git
   repository, documentation example, screenshot, chat message, or shared
   configuration file. Treat both as secrets.


Setup
=====

Administrator Setup
-------------------

Confirm that the Smarter CLI is connected to the intended platform:

.. code-block:: console

   smarter whoami
   smarter status

If the CLI has not been configured, run:

.. code-block:: console

   smarter configure

Use the account and environment values supplied for the NAPL Smarter
deployment.

Obtain an Anthropic API key from the Anthropic Console and store it only in
the approved Smarter deployment configuration or credential-management
mechanism.


Programmer Workstation Setup
----------------------------

Install the Smarter CLI using the current instructions at
``smarter.sh/cli`` and verify the installation:

.. code-block:: console

   smarter version

Configure the CLI if required:

.. code-block:: console

   smarter configure

Verify your identity and access:

.. code-block:: console

   smarter whoami
   smarter status

Install Claude Code using the current Anthropic installation instructions for
your operating system, then verify that the command is available:

.. code-block:: console

   claude --version


Concept Overview
================

Smarter sits between NAPL programmers and the external LLM provider. This
allows the organization to centralize provider configuration while giving
individual programmers controlled access through their own Smarter
credentials.

The main components are:

**Anthropic**
   The external LLM provider that operates Claude models.

**Claude model**
   The model that processes the programming request. The NAPL Smarter
   environment determines which models are approved and available.

**Provider**
   The Smarter resource that represents an external LLM service such as
   Anthropic.

**Provider credential**
   The organization-level credential Smarter uses when communicating with
   Anthropic. This is managed by the platform administrator.

**Smarter**
   The organizational gateway and management layer between developer tools
   and the upstream provider.

**Personal Smarter API credential**
   The programmer's credential for authenticating to Smarter. It is separate
   from the Anthropic provider credential.

**Smarter API Manifest (SAM)**
   A declarative YAML document used to describe Smarter resources. The Smarter
   CLI can generate an example manifest for the installed release.

The trust boundary is:

.. code-block:: text

   +-----------------------+       +----------------------+       +-----------+
   | Programmer workstation| HTTPS |        Smarter       | HTTPS | Anthropic |
   |                       | ----> |                      | ----> |           |
   | Claude Code           |       | authenticates user   |       | Claude    |
   | personal Smarter key  |       | manages provider key |       | model     |
   +-----------------------+       +----------------------+       +-----------+


Step-by-Step
============

Step 1: Make the Anthropic Credential Available to Smarter
-----------------------------------------------------------

The Anthropic credential must be available to the Smarter deployment using
the approved credential-management method for the environment.

Smarter documentation identifies the Anthropic deployment setting as:

.. code-block:: text

   SMARTER_ANTHROPIC_API_KEY=<Anthropic API key>

After configuring the credential, restart or reload the Smarter deployment
using the procedure established for the environment so the new value is
loaded.

.. warning::

   Do not commit the real Anthropic API key to source control.


Step 2: Inspect the Provider Manifest Schema
---------------------------------------------

Generate the Provider example supplied by the installed Smarter release:

.. code-block:: console

   smarter manifest provider -o yaml

Review the generated ``apiVersion``, ``kind``, ``metadata``, and ``spec``
fields before creating NAPL-specific provider configuration.

Because Provider features can change between releases, the manifest generated
by the installed version should be treated as the authoritative template.


Step 3: Apply or Confirm the Anthropic Provider
------------------------------------------------

If Anthropic is not already present and the installed Smarter release supports
Provider manifests for account administrators, apply the reviewed manifest:

.. code-block:: console

   smarter apply -f anthropic-provider.yaml

If Anthropic was initialized during platform deployment, confirm the existing
resource instead of creating a duplicate:

.. code-block:: console

   smarter get providers
   smarter describe provider anthropic -o yaml

Review the returned information and confirm that Anthropic is available in
the intended NAPL environment.


Step 4: Confirm Claude Models Are Available
--------------------------------------------

Use the Smarter console or current provider/resource views to confirm which
Claude models are available.

Do not design programmer onboarding around a model identifier that is not
exposed by the NAPL Smarter environment. Use an approved model or the
configured default.


Step 5: Obtain the Programmer's Smarter Credential
---------------------------------------------------

Use the NAPL-approved process to create or obtain a personal Smarter API
credential.

Verify the programmer's CLI access:

.. code-block:: console

   smarter whoami
   smarter status

The programmer uses this personal credential to authenticate to Smarter.
It is not the Anthropic API key configured by the administrator.


Step 6: Configure Claude Code to Use Smarter
---------------------------------------------

Claude Code normally communicates with Anthropic directly. For NAPL, configure
it to use the Smarter gateway instead.

The current Smarter Claude Code documentation uses these settings:

``ANTHROPIC_BASE_URL``
   The NAPL Smarter gateway URL supplied by the platform administrator.

``ANTHROPIC_AUTH_TOKEN``
   The programmer's personal Smarter API credential.

For example, in Claude Code's ``settings.json`` file:

.. code-block:: json

   {
     "env": {
       "ANTHROPIC_BASE_URL": "<NAPL_SMARTER_GATEWAY_URL>",
       "ANTHROPIC_AUTH_TOKEN": "<YOUR_PERSONAL_SMARTER_API_KEY>"
     }
   }

Typical file locations are:

* Linux/macOS: ``~/.claude/settings.json``
* Windows: ``%USERPROFILE%\.claude\settings.json``

If the file already contains other settings, merge the ``env`` object into
the existing configuration rather than replacing unrelated settings.

.. note::

   Smarter currently documents Claude Code integration as a prerelease
   feature. The integration is subject to change, so confirm the current
   Smarter documentation before applying these settings in a production
   environment.


Step 7: Open a Safe Test Project
---------------------------------

Use an existing local project that contains no data that is prohibited from
being sent to the approved NAPL AI service.

.. code-block:: console

   cd <YOUR_TEST_PROJECT>
   git status

Starting from a clean Git working tree makes it easier to review any changes
Claude Code proposes.


Step 8: Start Claude Code
--------------------------

From the project directory, start Claude Code:

.. code-block:: console

   claude

Claude Code should start using the Smarter gateway configured in the previous
step.


Step 9: Ask Claude Code to Inspect the Project
-----------------------------------------------

Use a small, non-destructive first task:

.. code-block:: text

   Review this project and give me a concise summary of its purpose,
   main components, and the commands I should use to test it.
   Do not modify any files yet.

Review the response and confirm that it refers to the local project rather
than returning only a generic programming explanation.


Step 10: Perform a Small Programming Task
------------------------------------------

Choose a low-risk change appropriate to the project. For example:

.. code-block:: text

   Identify one small documentation or code-quality improvement in this
   project. Explain the proposed change first. Do not modify files until I
   approve it.

If the proposed change is appropriate, authorize Claude Code to make it and
then review the result:

.. code-block:: console

   git diff

Run the project's existing test or validation command if one is available.


Step 11: Review Before Committing
----------------------------------

Treat Claude Code as a coding partner, not as an autonomous authority.

Review all proposed changes, tests, and assumptions before committing them.
Use the normal Git workflow to accept, revise, or discard the change.


Proof of Concept
================

The setup is successful when all of the following can be demonstrated:

* ``smarter get providers`` shows Anthropic in the expected environment.
* ``smarter describe provider anthropic`` returns the configured Provider.
* At least one approved Claude model is available through the Smarter
  environment.
* ``smarter whoami`` identifies the programmer's Smarter account.
* ``smarter status`` confirms that the platform is reachable.
* ``claude --version`` confirms Claude Code is installed.
* Claude Code starts from a local project using the configured Smarter
  gateway.
* Claude Code can inspect the project and return a project-specific response.
* A small proposed change can be reviewed with ``git diff`` before it is
  committed.

A successful project-inspection response is sufficient to demonstrate the
basic end-to-end workflow:

.. code-block:: text

   Programmer -> Claude Code -> Smarter -> Anthropic -> Claude model


Troubleshooting
===============

**Anthropic does not appear in the provider list**
   Confirm that the administrator is connected to the correct Smarter
   environment and that the provider was either initialized during deployment
   or successfully applied.

**The Provider manifest is rejected**
   Generate a fresh example with ``smarter manifest provider -o yaml`` and
   compare the field names and structure with the current manifest.

**The provider credential is missing or invalid**
   Confirm that the Anthropic credential exists in the deployment's approved
   secret-management mechanism. Do not place a real API key directly in a
   Git-tracked manifest.

**Provider verification fails**
   Check outbound connectivity, provider URL configuration, credential
   validity, and the Smarter application logs.

**The expected Claude model is not available**
   Check the models currently exposed by the configured Anthropic provider.
   Do not assume that a model identifier from an older tutorial is still
   available.

**``smarter whoami`` fails**
   Re-run ``smarter configure`` and verify the root domain, account number,
   username, environment, and personal Smarter API credential.

**Claude Code connects directly to Anthropic instead of Smarter**
   Verify that ``ANTHROPIC_BASE_URL`` is present in the Claude Code
   configuration and points to the NAPL Smarter gateway.

**Authentication fails after Claude Code starts**
   Verify that ``ANTHROPIC_AUTH_TOKEN`` contains the programmer's personal
   Smarter API credential, not the platform's Anthropic API key.

**The Smarter CLI works but Claude Code does not**
   Check the Claude Code settings file for malformed JSON, an incorrect
   gateway URL, or an invalid credential. Restart Claude Code after changing
   its configuration.

**The response is unrelated to the project**
   Confirm that Claude Code was launched from the intended project directory
   and that the expected project files are available to the session.

**You are unsure whether project data may be sent to the AI service**
   Stop and follow NAPL's information-handling and development policies before
   sending the material. Successful technical configuration does not override
   organizational data-handling requirements.


See Also
========

* :doc:`/smarter-platform/adding-an-llm-provider`
* :doc:`/smarter-resources/smarter-provider`
* :doc:`/smarter-framework/smarter-cli`
* :doc:`/smarter-platform/api-keys`