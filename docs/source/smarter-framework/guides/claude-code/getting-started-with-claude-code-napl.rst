======================================================
NAPL Programmer Onboarding for Claude Code in Smarter
======================================================

.. contents:: Table of Contents
   :local:
   :depth: 2

Goal
====

Use Smarter and the NAPL Claude Code rollout to complete a small programming
task as a virtual CoPilot coding pair.

After completing this guide, you should be able to:

- verify that your Smarter account can access the platform from the CLI
- confirm that the Anthropic provider has been onboarded for your account
- locate the Claude Code chatbot assigned to the programming area
- run a short coding session and inspect the result

Prerequisites
=============

This tutorial assumes that you already have:

- a Smarter account
- the ability to log in to Smarter
- a Smarter API key issued through your internal onboarding process
- the Smarter CLI installed locally
- normal programmer-level familiarity with terminals, YAML, and source control

.. note::

   This is a programmer self-onboarding tutorial, not an administrator setup
   guide. Infrastructure setup, IDE integration, and cost-tracking controls
   are outside the scope of this page.

Setup
=====

Before you begin, make sure the following are true:

1. You can authenticate to Smarter from the CLI.
2. Your workstation can reach the Smarter environment used by your team.
3. The NAPL rollout team has already completed the provider onboarding work
   described in :doc:`/smarter-resources/provider/adding-anthropic-provider`.

Start by verifying your CLI access with the API key you were issued:

.. code-block:: bash

   smarter whoami --api_key YOUR_API_KEY_HERE

Then verify that the platform is reachable:

.. code-block:: bash

   smarter status

.. warning::

   The current Smarter codebase still documents the built-in
   ``Chatbot.spec.config.provider`` values as ``openai``, ``metaai``, and
   ``googleai`` in
   :doc:`/smarter-resources/chatbots/models`.
   For this tutorial, assume that NAPL's platform team has already completed
   the additional rollout work needed to expose the Anthropic-backed Claude Code
   experience to programmers. If the Claude Code chatbot is not present in your
   account, stop here and contact the rollout team rather than editing platform
   manifests yourself.

Concept Overview
================

There are three ideas to keep separate:

Provider onboarding
   An administrator registers Anthropic with Smarter so the platform can verify
   and manage that provider centrally. That is covered in
   :doc:`/smarter-resources/provider/adding-anthropic-provider`.

Chatbot access
   Programmers do not interact with raw providers directly. In normal Smarter
   workflows, they interact with a Chatbot resource that has already been
   prepared for their team.

Programmer self-onboarding
   The programming area's job is to confirm access, find the assigned coding
   assistant, and begin using it for real development work.

In practical terms, your self-onboarding flow is:

1. Authenticate to Smarter.
2. Confirm the Anthropic provider rollout exists.
3. Find the Claude Code chatbot assigned to your account.
4. Use that chatbot for a small coding task.

.. seealso::

   - :doc:`/smarter-resources/provider/adding-anthropic-provider`
   - :doc:`/smarter-resources/smarter-provider`
   - :doc:`/smarter-resources/smarter-chatbot`
   - :doc:`/smarter-platform/api-keys`
   - :doc:`/smarter-framework/smarter-cli`

Step-by-Step
============

Step 1: Confirm your identity
-----------------------------

Run:

.. code-block:: bash

   smarter whoami --api_key YOUR_API_KEY_HERE

This should return information about your user and account. If it does not,
fix authentication before doing anything else.

Step 2: Confirm the platform is healthy
---------------------------------------

Run:

.. code-block:: bash

   smarter status

The CLI status command is backed by the platform's non-brokered status API and
returns platform health data. Use this as a baseline check before troubleshooting
chatbot or provider behaviour.

Step 3: Confirm that Anthropic has been onboarded
-------------------------------------------------

Run:

.. code-block:: bash

   smarter get providers
   smarter describe provider Anthropic

For this tutorial to work, the provider rollout completed by the NAPL
administrator must already exist in your environment.

What you are looking for:

- a provider named ``Anthropic`` in the provider list
- a provider description that clearly corresponds to the Anthropic rollout
- a status block indicating that the provider is active and verified

.. note::

   If you do not have permission to view providers directly, that is still a
   rollout issue rather than a programmer workflow issue. Ask the Smarter
   administrator to confirm that the Anthropic provider was applied and
   verified for your account.

Step 4: Find the programming area's Claude Code chatbot
-------------------------------------------------------

Run:

.. code-block:: bash

   smarter get chatbots

Look for the chatbot that your team has been told to use for Claude Code in the
programming area.

Once you have the name, inspect it:

.. code-block:: bash

   smarter describe chatbot <chatbot-name> -o yaml

Use this output to verify that:

- the chatbot exists in your account
- it is clearly intended for coding assistance
- its welcome message and example prompts match the programming use case

Step 5: Start your first coding session
---------------------------------------

Run:

.. code-block:: bash

   smarter chat <chatbot-name>

When the interactive session opens, give it a bounded programming prompt. Use a
task that is small enough to validate quickly.

Example prompt:

.. code-block:: text

   Write a Python function named normalize_account_number(raw: str) -> str
   that converts a 12-digit string into the Smarter account format
   9999-9999-9999. Then write three pytest tests for valid input,
   non-digit input, and incorrect length.

Why this is a good onboarding prompt:

- it is concrete and easy to verify
- it produces both implementation code and tests

Step 6: Review the response like a programmer
---------------------------------------------

Do not stop at "the model answered." Read the output as you would review a
junior teammate's pull request.

Check for:

- correct Python syntax
- the expected ``9999-9999-9999`` formatting behavior
- sensible error handling
- pytest tests that actually exercise the stated cases

If the first answer is incomplete, keep iterating in the same session. A good
follow-up prompt is:

.. code-block:: text

   Refactor the function to raise ValueError with clear messages and update
   the tests accordingly.

Step 7: Use the Workbench when you need a UI-based review pass
--------------------------------------------------------------

If your Smarter deployment exposes the Prompt Engineer Workbench for the
assigned chatbot, repeat the same task there to compare the experience with the
CLI session. The repository documents Workbench-based chatbot usage in
:doc:`/smarter-resources/smarter-chatbot`.

Use the Workbench for:

- prompt iteration
- reviewing long responses in a browser
- comparing alternative prompts before you reuse one in your normal workflow

Proof of Concept
================

The tutorial is successful when you can demonstrate all of the following:

- ``smarter whoami --api_key YOUR_API_KEY_HERE`` returns your user and account
- ``smarter status`` confirms that the platform is reachable
- ``smarter get chatbots`` shows the Claude Code chatbot assigned to your team
- ``smarter chat <chatbot-name>`` returns a coding response to your test prompt

For the sample prompt in this tutorial, the expected result is:

- one Python function that formats a 12-digit account number as
  ``9999-9999-9999``
- three pytest tests covering the requested cases
- an answer you can review and refine in follow-up prompts

That is enough to prove that the programming area can begin using Smarter with
Claude Code as a virtual CoPilot workflow.

Troubleshooting
===============

``smarter whoami`` returns an authentication error
--------------------------------------------------

Your API key is missing, invalid, expired, or tied to the wrong environment.
Re-run the command with the API key you were issued and verify that you are
targeting the correct Smarter environment.

``smarter status`` does not return healthy platform information
---------------------------------------------------------------

This is not a Claude Code problem. It means the Smarter platform itself is not
reachable or not healthy enough for onboarding. Escalate to the infrastructure
or platform team.

``Anthropic`` does not appear in ``smarter get providers``
----------------------------------------------------------

The provider rollout has not been completed for your account, or you do not
have visibility into provider resources. This blocks the programmer onboarding
workflow and should be escalated to the Smarter administrator.

No coding chatbot appears in ``smarter get chatbots``
-----------------------------------------------------

Your account has not yet been assigned the programming area's chatbot, or the
rollout team has not created it yet. This is the most likely failure point for
an otherwise healthy account.

The chatbot responds, but the output is weak or incomplete
----------------------------------------------------------

Treat the model like a pair programmer, not a compiler. Narrow the task,
specify the language and framework, and ask for tests or constraints
explicitly.

.. warning::

   Do not attempt to solve a missing Claude Code rollout by editing provider or
   chatbot manifests as an end user. Administrator provider onboarding is a
   separate responsibility from programmer self-onboarding.
