Adding an Anthropic Provider to Smarter
========================================

Goal
----

Add Anthropic as an LLM provider in Smarter and register a Claude model so it can be used for coding-assistant workflows.

Prerequisites
-------------

This tutorial assumes that you:

* already have a working Smarter account
* can sign in to the Smarter web console
* already have an Anthropic API key
* understand basic LLM terms such as provider, model, and API key
* are comfortable following technical setup steps without screenshots

Setup
-----

Before you begin, gather the following:

* an Anthropic API key
* the Claude model name you plan to register
* the base endpoint information required by your Smarter deployment
* the account permissions needed to manage providers

Concept Overview
----------------

In Smarter, a **provider** is the external LLM service integration. A **model** is the individual model entry exposed by that provider.

For this exercise:

* **Provider** = Anthropic
* **Model** = a Claude model that your team will use with Claude Code

The high-level flow is:

1. create or open the Anthropic provider entry
2. store the API credential securely in Smarter
3. register the Claude model under that provider
4. validate the provider/model pairing
5. use the model in downstream Smarter resources

Step-by-Step
------------

1. Sign in to Smarter.

2. Open the area used for provider management.

3. Create a new provider entry, or select the existing Anthropic provider if one already exists.

4. Enter the provider details required by your Smarter installation. At minimum, confirm the provider name, authentication details, and endpoint values expected by the form.

5. Paste in the Anthropic API key and save it using the platform's credential handling workflow.

6. Add a model record beneath the provider. Use a clear internal display name so programmers can identify it quickly.

7. In the model configuration, enter the Claude model identifier required by your environment.

8. Save the model.

9. Run the provider or model verification check if your installation exposes one. Verification confirms that Smarter can reach the provider and that the configured model is compatible with the expected feature set.

10. Confirm that the model now appears as an available option inside the relevant Smarter resource or authoring workflow.

Recommended Naming Convention
-----------------------------

Use a simple naming convention so your team can distinguish provider records from model records.

Example:

* Provider display name: ``Anthropic``
* Model display name: ``Claude Code - Team Standard``
* Optional technical alias: ``anthropic-claude-code``

Proof of Concept
----------------

A successful proof of concept is simple:

* the Anthropic provider saves without credential errors
* the Claude model saves successfully
* the model passes validation
* the model appears as a selectable LLM option in Smarter

One practical smoke test is to open a coding-oriented prompt or resource and confirm that the Claude model can be selected and invoked.

Troubleshooting
---------------

**Problem: The provider saves, but the model does not validate.**

Check that the model identifier exactly matches the Claude model name expected by your Smarter deployment.

**Problem: Authentication fails.**

Re-enter the Anthropic API key and confirm that the key is active and not restricted incorrectly.

**Problem: The model is not visible to programmers.**

Check account permissions, provider visibility, and whether the model was attached to the correct account or scope.

**Problem: The provider exists, but requests still fail.**

Re-check the endpoint configuration and run the platform verification step again.

**Problem: The UI looks different from this tutorial.**

The Smarter Provider app is under active development. Use this tutorial as the process guide, but follow the labels and controls shown in your current deployment.

Expected Outcome
----------------

At the end of this tutorial, your Smarter environment should expose an Anthropic-backed Claude model that programmers can use in Smarter-based coding workflows.
