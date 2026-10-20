Getting Started with Anthropic in Smarter
=========================================

Goal
----

We will configure Anthropic as an LLM provider in Smarter and use a Claude
model through an LLM client.

Prerequisites
-------------

Readers should understand Git, environment variables, REST APIs, YAML, and
basic terminal commands. A Smarter account and an Anthropic API key are
required. Claude Code is Anthropic's coding tool; Claude Sonnet is the
model used in this example.

Setup
-----

#. Create an API key in the
   `Anthropic Console <https://platform.claude.com/settings/keys>`_.
#. Configure ``ANTHROPIC_API_KEY`` in the environment used by Smarter.
#. Ensure Smarter and its database and dependent services are running.
#. Never commit API keys or other secrets to Git.

Concept Overview
----------------

Smarter separates providers from LLM clients. A provider defines the API
connection and authentication. An LLM client selects a provider and model
and configures prompts and generation settings.

The Anthropic provider uses ``https://api.anthropic.com/v1/`` and the
``x-api-key`` and ``anthropic-version`` authentication headers. The API key
is a secret; the model identifier is configuration.

Step-by-Step
------------

#. **Configure the key.** Set ``ANTHROPIC_API_KEY`` in the runtime
   environment where Smarter executes.

#. **Initialize providers.** From the Smarter application environment, run::

       python manage.py initialize_providers

   Run this command where the application settings, database, and dependent
   services are reachable. In a container deployment, execute it in the
   appropriate application container.

#. **Configure the LLM client.** Set the client provider to ``anthropic``
   and its model to ``claude-sonnet-4-6``. For example, the relevant YAML
   settings are::

       spec:
         apiKey: null
         config:
           prompt:
             provider: anthropic
             defaultModel: claude-sonnet-4-6

   Keep the API key in the runtime environment, not in the manifest.

#. **Deploy and test.** Deploy the client using your Smarter installation's
   workflow. Submit the prompt ``Return READY and nothing else.``

Proof of Concept
----------------

A successful request returns a Claude-generated response. For the test
prompt above, the expected result is::

    READY

The exact response can vary with model behavior and client configuration.

Troubleshooting
---------------

* **Missing API key:** Verify that the application runtime has
  ``ANTHROPIC_API_KEY`` set.
* **Authentication failure:** Check that the key is valid and API access
  is enabled for your Anthropic account.
* **Provider initialization fails:** Check database connectivity, dependent
  services, and application logs.
* **Unknown model:** Confirm model availability for your account and check
  the configured provider and model identifiers.
* **No client response:** Verify that the client is deployed and inspect
  application and worker logs.

References
----------

* `Anthropic API documentation
  <https://platform.claude.com/docs/en/api/overview>`_
* `Anthropic Console
  <https://platform.claude.com/settings/keys>`_
