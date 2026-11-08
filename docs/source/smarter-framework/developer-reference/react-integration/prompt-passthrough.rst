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

The Prompt Passthrough is a page of the single-page console (:doc:`ADR-035 </adr/035-single-page-app>`), at
``/dashboard/passthrough/``, while ``smarter_settings.enable_dashboard_passthrough_prompt`` is on.
``@smarter/console`` renders ``@smarter/prompt-passthrough``'s ``PromptPassthrough`` inside its frame, with the
urls of the passthrough api, ``/api/v1/prompts/passthrough/``, and of the providers api,
``/api/web/dashboard/passthrough/providers/``, and, while users can view their server logs, the url of the log
stream, from which its Server Logs tab streams the server logs of each prompt that it sends. The package has no
build of its own; ``npm run dev`` in it renders the page against the Django dev server's api. Django answers the
path with the console's page, and keeps its url name.

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
