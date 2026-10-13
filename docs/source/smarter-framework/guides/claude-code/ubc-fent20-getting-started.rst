Getting Started: Claude Code with Smarter
=========================================

Goal
----

Use Claude Code with Smarter to complete a small, testable programming task through an approved Anthropic model, while keeping credentials secure and retaining normal developer review.

Prerequisites
-------------

This tutorial assumes that you:

* already have a Smarter account and can log in
* have access to a project in a local Git working tree
* are comfortable with a terminal, Git, and your project's programming language
* understand how to run tests and review code changes
* have access to an Anthropic provider and Claude model configured in Smarter, or can ask a Smarter administrator to provide them
* understand that model-generated code must be reviewed and tested before use

Setup
-----

Before starting, confirm that the Anthropic provider and Claude model are configured in Smarter. If they are not, follow the companion tutorial, *Adding an Anthropic Provider to Smarter*, or contact your administrator.

You will also need:

* Claude Code installed and authenticated according to your organization's approved setup
* access to the Smarter endpoint and authentication method supported by your deployment
* permission to use the configured Claude model
* a small, non-sensitive programming task for the first run

**Important:** Smarter provider configuration and Claude Code client configuration are not automatically the same thing. Do not assume that signing in to the Smarter web console configures your local Claude Code client. Use the endpoint, authentication, and integration method documented for your specific Smarter deployment. Never place API keys in source control.

Concept Overview
----------------

Anthropic provides Claude models. Smarter manages access to configured LLM providers and exposes approved models to authorized users and applications. Claude Code is a coding tool that can inspect a project and assist with programming tasks.

The intended workflow is:

#. An administrator configures Anthropic as a provider in Smarter.
#. A Claude model is registered and validated.
#. The programmer configures Claude Code to use the supported Smarter integration, if the deployment provides one.
#. Claude Code is used on a small task in a local project.
#. The programmer reviews the proposed changes and runs the project's tests.

The key integration detail is the API endpoint and authentication contract. Configure the client only with values documented for your Smarter installation. Do not invent an endpoint or assume that a provider's direct API credentials can be used interchangeably with Smarter credentials.

Step-by-Step
------------

1. **Confirm model availability.**

   Sign in to Smarter and verify that your account can access the approved Anthropic-backed Claude model. If the model is unavailable, ask your administrator to check provider configuration, model registration, and account permissions.

2. **Confirm the supported Claude Code integration.**

   Consult your organization's Smarter documentation for the endpoint, authentication method, and model identifier supported for Claude Code. If your deployment does not expose a compatible interface, ask the administrator which supported client or workflow should be used. Do not assume that selecting a model in the Smarter web console connects the local Claude Code application.

3. **Install and verify Claude Code.**

   Follow the official installation instructions approved for your operating system. Open a terminal and verify that the executable is available using the command documented for your installed version.

4. **Configure the client.**

   Apply the endpoint, authentication, and model settings documented for your deployment. Store credentials in the approved secret store or environment configuration. Do not commit secrets, print them in logs, or paste them into prompts.

5. **Open a test project.**

   Change to a non-production Git working tree. Check the current state before making changes:

   ::

      git status

   Start with a clean branch or ensure that existing uncommitted work is safely preserved.

6. **Choose a small programming task.**

   For example, ask Claude Code to explain a utility function, suggest a small refactor, or draft a unit test. Avoid production credentials, customer data, and other sensitive information.

7. **Provide precise instructions.**

   Specify the relevant files, programming language, expected behavior, constraints, and acceptance criteria. Ask for a minimal change and an explanation of the proposed solution.

8. **Inspect the proposed changes.**

   Review the diff. Check correctness, security, maintainability, dependencies, and compliance with team conventions. Reject changes that are unnecessary or unsafe.

9. **Run tests locally.**

   Use the project's documented test and lint commands. Resolve failures before accepting the change. Do not treat a successful model response as evidence that the code works.

10. **Record the result.**

    If the change passes review and tests, use your normal Git workflow to commit it. Keep the change small enough for another developer to review.

Example Prompt
-------------

Use a prompt such as the following for a first exercise:

::

   Task: Add unit tests for the existing date-formatting helper.
   Context: This is a local development project.
   Constraints:
   - Follow the project's existing test conventions.
   - Do not change production behavior.
   - Do not add dependencies.
   - Include a normal case and an invalid-input case.
   Acceptance criteria:
   - The tests are readable and deterministic.
   - Existing tests continue to pass.
   Output:
   Explain the proposed changes and identify the tests to run.

Proof of Concept
----------------

The proof of concept is complete when:

* Claude Code can perform a small task using the approved integration and model.
* The resulting suggestion is relevant to the selected project.
* The programmer can inspect the proposed diff.
* The project's relevant tests pass.
* No API key or other secret is exposed in the source tree or Git history.

For example, use Claude Code to draft tests for a small helper, review the diff, run the test suite, and verify the results independently.

Troubleshooting
---------------

**The Claude model is missing in Smarter.**

Ask the administrator to verify the Anthropic provider, registered model, validation status, and your account permissions.

**Claude Code cannot connect through Smarter.**

Verify the documented endpoint, authentication method, network access, and model identifier. Confirm that your deployment supports the client interface you are attempting to use.

**Authentication fails.**

Check that the configured credential is valid for the selected integration and has not expired. Do not substitute an Anthropic API key for a Smarter credential unless the deployment documentation explicitly requires it.

**The model returns an unsupported-model error.**

Check the exact model identifier and whether the model is enabled for your account and integration.

**Generated code fails tests.**

Inspect the diff, reproduce the failure, and provide Claude Code with the relevant error output and expected behavior. Never accept a change simply because it looks plausible.

**The response contains sensitive information or unsafe code.**

Stop, do not commit the output, and follow your organization's security and incident-reporting procedures.

**The documented setup does not match the deployment.**

Use the current deployment documentation or ask the Smarter administrator for the supported integration procedure. Do not guess configuration values.

Expected Outcome
----------------

After completing this tutorial, a programmer should understand the relationship between Claude Code, Smarter, and the configured Anthropic model; know how to verify the supported integration; and be able to complete and test a small coding task without exposing credentials or bypassing normal engineering review.