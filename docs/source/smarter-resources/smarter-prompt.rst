Smarter Prompt
===============

Overview
--------

Smarter Prompt manages :py:class:`prompt sessions <smarter.apps.prompt.views.views.SmarterPromptSession>` and the
integration between the Smarter backend and the :doc:`ReactJS chat component <../smarter-framework/developer-reference/react-integration/smarter-chat>`
used to manage sessions in the Smarter Chat HTML integration, as well as in the :doc:`command-line interface (CLI) <../smarter-framework/smarter-cli>`.
It is chiefly responsible for storing and retrieving
:py:class:`prompt sessions <smarter.apps.prompt.models.Chat>` and messages in the
database, serving the :doc:`configuration object <prompt/example-config>` to the
ReactJS chat component, handling REST API :doc:`prompt requests <prompt/example-request>`,
serving :doc:`prompt responses <prompt/example-response>`, and orchestrating the
Smarter resources associated with a session, including :doc:`Account <smarter-account>`,
:doc:`LLMClient <smarter-llmclient>`, and :doc:`Plugin <smarter-plugin>`.

Smarter sessions do not expire unless deleted by an administrator as part of MySQL database disk space maintenance operations.


.. note::

  Smarter sessions are distinct from Smarter LLMClients. An LLMClient is a resource that defines the
  configuration of an llmclient, including its system prompt, plugins, and other settings. A session,
  by contrast, is an instance of a conversation with an llmclient, comprising the complete history of
  messages exchanged during that conversation.

  Smarter sessions originate in Smarter Prompt, are passed to the ReactJS component as part of the
  configuration object, and are stored as browser cookies, identified by a GUID-like string that,
  with a high level of certainty, uniquely identifies the session. Sessions are specific to the device
  and browser in which they were created; a session started on one device or browser cannot be
  continued on another.evice/browser, you cannot continue that session on another device/browser.

Usage
-----

.. code-block:: bash

  # Smarter Prompt Engineer Workbench
  curl -X POST http://localhost:9357/api/v1/llm-clients/9/chat/?session_key=e5c0368d6d7201b60f4f20c470f4b5ba36faf45e80ddbe8b04b6cf20f33167a7

  # Deployed Smarter LLMClient - Alpha
  curl -X GET https://stackademy.3141-5926-5359.alpha.api.example.com/chat/?session_key=<SESSION-KEY>

  # Deployed Smarter LLMClient - Production
  curl -X GET https://stackademy.3141-5926-5359.api.example.com/chat/?session_key=<SESSION-KEY>

.. seealso::

    - :doc:`Smarter Chat <../smarter-framework/developer-reference/react-integration/smarter-chat>`
    - :doc:`Smarter CLI <../smarter-framework/smarter-cli>`
    - :doc:`Smarter API <../smarter-framework/smarter-api>`
    - :doc:`Smarter Journal <../smarter-framework/developer-reference/smarter-journal>`
    - :doc:`Smarter Account <../smarter-resources/smarter-account>`
    - :doc:`Smarter LLMClients <../smarter-resources/smarter-llmclient>`
    - :doc:`Smarter Plugins <../smarter-resources/smarter-plugin>`


Technical Reference
-------------------

.. toctree::
   :maxdepth: 1


   prompt/example-config
   prompt/example-request
   prompt/example-response
   prompt/api
   prompt/const
   prompt/manifest
   prompt/models
   prompt/functions
   prompt/management
   prompt/signals
   prompt/tasks
   prompt/templatetags
   prompt/urls
   prompt/views
