Smarter Prompt
===============

Smarter Prompt manages :py:class:`prompt sessions <smarter.apps.prompt.views.SmarterChatSession>` and integrations between the Smarter backend and the
:doc:`ReactJS chat component <../smarter-framework/smarter-react-ui>` used for managing sessions in the Smarter React UI in html integrations,
as well as in the :doc:`command-line interface (CLI) <../smarter-framework/smarter-cli>`.

Smarter Prompt is chiefly responsible for:

 - Storing and retrieving :py:class:`prompt sessions <smarter.apps.prompt.models.Chat>` and messages in the database.
 - Serving the :doc:`configuration object <prompt/example-config>` to the :doc:`ReactJS chat component <../smarter-framework/smarter-react-ui>`.
 - Handling REST API :doc:`prompt requests <prompt/example-request>`.
 - Serving :doc:`prompt responses <prompt/example-response>`.
 - Orchestrating the Smarter resources for the session
   (
   :doc:`Account <smarter-account>`,
   :doc:`Chatbot <smarter-chatbot>`,
   :doc:`Plugin <smarter-plugin>`)

Smarter sessions do not expire unless deleted by an administrator as part of MySQL database disk space maintenance operations.

.. note::

  Smarter sessions are distinct from Smarter Chatbots. A Smarter Chatbot is a resource that defines
  the configuration of a chatbot, including its system prompt, plugins, and other settings. A Smarter session,
  on the other hand, is an instance of a conversation with a chatbot, which includes the
  complete history of messages exchanged during that conversation.

  Smarter sessions originate in Smarter Prompt, are passed to the ReactJS component as part of the
  configuration object, and are stored as browser cookies. Smarter session identifiers are a
  GUID-like string that, with a high level of certainty, uniquely identify a session.

  Smarter sessions are distinct to the device/browser in which they are created. If you start a session
  on one device/browser, you cannot continue that session on another device/browser.

.. seealso::

    - :doc:`Smarter React UI <../smarter-framework/smarter-react-ui>`
    - :doc:`Smarter CLI <../smarter-framework/smarter-cli>`
    - :doc:`Smarter API <../smarter-framework/smarter-api>`
    - :doc:`Smarter Journal <../smarter-framework/smarter-journal>`
    - :doc:`Smarter Account <../smarter-resources/smarter-account>`
    - :doc:`Smarter Chatbots <../smarter-resources/smarter-chatbot>`
    - :doc:`Smarter Plugins <../smarter-resources/smarter-plugin>`


.. toctree::
   :maxdepth: 1
   :caption: Technical Reference


   prompt/example-config
   prompt/example-request
   prompt/example-response
   prompt/api
   prompt/models
   prompt/sam
   prompt/const
   prompt/functions
   prompt/providers
   prompt/signals
   prompt/tasks
   prompt/urls
   prompt/views
