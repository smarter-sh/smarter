Prompt Passthrough React Component
===================================

The Prompt Passthrough React component provides a powerful and user-friendly
interface for constructing and sending custom API requests to a variety of large
language model (LLM) providers.

.. note::

  Users -- especially students and researches who are new to working with LLM APIs --
  can be productive in seconds, without any need for them to write computer code
  nor set up complex REST API clients. The Prompt Passthrough templates include
  pre-built configurations for all common use cases, adapted for popular providers
  like OpenAI, GoogleAI, Anthropic, and HuggingFace.


Prompt Passthrough is designed to be a versatile tool for both experimentation and
production use. It includes features like provider and template selection,
a Monaco-powered JSON editor, and real-time display of both requests
and responses, it empowers users to experiment with and debug LLM APIs directly
from the browser. CSRF protection is seamlessly integrated, and the component’s
modular design makes it easy to extend or adapt for different providers and
workflows. This makes it an ideal tool for developers and researchers who want to
interactively explore, test, and integrate LLM capabilities without leaving their
dashboard.

Importantly, the Prompt Passthrough component runs on top of the complete suite
of Smarter's AI resource management features, including role-based access control,
shared resource management, and advanced logging and usage tracking, ensuring
secure and efficient operation within your organization's AI ecosystem. The underlying
API endpoints themselves are provisioned via Smarter's LLM Provider resource module.

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/prompt-passthrough-react-component.png
   :alt: Prompt Passthrough React Component Screenshot
   :class: screenshot
   :align: center
   :width: 100%

.. toctree::
   :maxdepth: 1
   :caption: Prompt Passthrough Component Technical Reference

   prompt-passthrough/api
   prompt-passthrough/django-view
   prompt-passthrough/example-usage
   prompt-passthrough/react-component
