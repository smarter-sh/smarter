Smarter Provider
=====================

.. warning::

   **The Smarter Provider app contains edge features that are under active development. Some
   features may be incomplete, untested, or subject to change. Use at your own risk.**

   Legacy LLM providers (OpenAI, Anthropic, MetaAI, GoogleAI and DeepSeek) are stable and will work as expected.

Overview
--------

The Smarter Provider app connects third-party LLM providers to the Smarter Platform.
Rather than wiring each provider in through manual, one-off configuration, it
exposes a structured onboarding process that validates a provider's models before
they become available to Smarter Resources. As part of that process, the app runs
a battery of verification checks confirming that a provider's models are compatible
with the Smarter Resource feature set, and it re-runs those checks periodically
so compatibility doesn't silently drift over time.

How these features get deployed depends on the installation. Some organizations
restrict Provider onboarding to internal administrators and treat it purely as
an admin function. Others open it up publicly, letting independent LLM providers
register themselves and self-onboard their models directly.


.. note::

  The Smarter Provider app is included in v0.11.0 and later. It shifts management of LLM provider
  API credentials from an IT and DevOps responsibility to the Account administrators.


.. seealso::

    - :doc:`Smarter Installation Guide <../smarter-platform/installation>`
    - :doc:`OpenAI Getting Started Guide <../smarter-framework/guides/openai-api-getting-started-guide>`
    - :doc:`Adding an LLM Provider <../smarter-platform/adding-an-llm-provider>`

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   provider/api
   provider/const
   provider/management
   provider/manifest
   provider/models
   provider/serializers
   provider/services
   provider/signals
   provider/tasks
   provider/utils
   provider/verification
   provider/views
