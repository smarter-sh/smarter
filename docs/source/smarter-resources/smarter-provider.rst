Smarter Provider
=====================

.. warning::

   **The Smarter Provider app contains edge features that are under active development. Some
   features may be incomplete, untested, or subject to change. Use at your own risk.**

   Legacy LLM providers (OpenAI, Anthropic, MetaAI, GoogleAI and DeepSeek) are stable and will work as expected.

Overview
--------

The Smarter Provider app is responsible for managing 3rd party LLM provider
integrations to the Smarter Platform. It provides services for onboarding
and validating LLM provider models, to make these available for use in Smarter Resources.
It ensures and periodically verifies compatibility with the Smarter Resource feature
set by performing a series of verification checks on the provider models.

The Smarter Provider app is included in v0.11.0 and later.
It shifts management of LLM provider API credentials from an IT
and devops responsibility, to the Account administrators.

Depending on the nature of your Smarter installation, you may choose to
use the Smarter Provider features internally as admin functions, or expose these
publicly so that independent LLM providers can register themselves and
self-onboard their models to your Smarter installation.

.. seealso::

    - :doc:`Smarter Installation Guide <../smarter-platform/installation>`
    - :doc:`OpenAI Getting Started Guild <../smarter-framework/guides/openai-api-getting-started-guide>`

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   provider/api
   provider/models
   provider/sam
   provider/serializers
   provider/const
   provider/management-commands
   provider/signals
   provider/tasks
   provider/utils
   provider/verification
