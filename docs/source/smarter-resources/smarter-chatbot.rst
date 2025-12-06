Smarter Chatbot
================

.. attention::

   The term 'ChatBot' is used interchangeably with 'Agent' and 'Workflow Unit' throughout
   this documentation.

Smarter Chatbots are highly advanced conversational agents designed to provide
intelligent and context-aware interactions with human users as well as
fully automated workflows. They leverage the vanguard
of generative AI text completion technology to deliver personalized and efficient
responses. Namely, these chatbots leverage the Smarter Plugin architecture, which
provides extensible tool integration capabilities, including secure access to
to private, secure data sources and external APIs.

ChatBots are recognized by the yaml-based :doc:`Smarter API Manifest (SAM) <../smarter-framework/smarter-api>` architecture,
facilitating both behavioral and visual customization. This allows developers to
tailor the chatbot's functionality and appearance to meet specific use cases and
user preferences.

ChatBots are managed with the :doc:`Smarter command-line interface (CLI) <../smarter-platform/cli>`.

.. toctree::
   :maxdepth: 1
   :caption: Technical Reference

   chatbots/api
   chatbots/models
   chatbots/sam
   chatbots/serializers
   chatbots/react-ui
   chatbots/helper
   chatbots/kubernetes-ingress
   chatbots/management-commands
   chatbots/middleware
   chatbots/tasks
   chatbots/signals
   chatbots/urls


.. literalinclude:: ../../../smarter/smarter/apps/plugin/data/stackademy/chatbot-stackademy-sql.yaml
   :language: yaml
   :caption: Example Smarter Manifest

Sandbox Mode
------------

Smarter Chatbots can be operated in a 'Sandbox Mode', which restricts their
capabilities to ensure safe experimentation and testing. In this mode, chatbots
are only addressable using URL schemes that authenticate with Django sessions.
That is, they cannot be accessed via API keys nor will they function using
URL schemas such as `stackademy.1234-5678-9012.api.example.com`.

An example sandbox mode url:

  ``https://platform.smarter.sh/workbench/stackademy-sql/chat/``



Deploying
---------

Deploy a Smarter Chatbot using the Smarter CLI. For example:

.. code-block:: bash

  smarter deploy chatbot stackademy-sql

.. code-block:: bash

  smarter deploy chatbot -h
  Deploys a ChatBot:

  smarter deploy chatbot <name> [flags]

  The Smarter API will deploy the ChatBot.

  Usage:
    smarter deploy chatbot <name> [flags]

  Flags:
    -h, --help   help for chatbot

  Global Flags:
        --api_key string         Smarter API key to use
        --config string          config file (default is $HOME/.smarter/config.yaml)
        --environment string     environment to use: local, alpha, beta, next, prod. Default is prod
    -o, --output_format string   output format: json, yaml (default "json")
    -v, --verbose                verbose output



Updating
--------

Update a Smarter Chatbot using the Smarter CLI. For example:

.. code-block:: bash

  smarter apply -f path/to/chatbot-manifest.yaml


Deleting
--------

Delete a Smarter Chatbot using the Smarter CLI. For example:

.. code-block:: bash

  smarter delete chatbot stackademy-sql


Testing
-------

Test your Smarter Chatbot using the Smarter Workbench while in Sandbox Mode.

.. raw:: html

   <div style="text-align: center;">
     <video src="https://cdn.smarter.sh/videos/read-the-docs2.mp4"
            autoplay loop muted playsinline
            style="width: 100%; height: auto; display: block; margin: 0; border-radius: 0;">
       Sorry, your browser doesn't support embedded videos.
     </video>
     <div style="font-size: 0.95em; color: #666; margin-top: 0.5em;">
       <em>Smarter Prompt Engineering Workbench Demo</em>
     </div>
   </div>
   <br/>


Monitoring
----------

Use ad hoc Sql queries to monitor your Smarter Chatbot's production performance and usage.

See:

 - :py:class:`smarter.apps.chatbot.models.ChatBotRequests`
 - :py:class:`smarter.apps.plugin.models.PluginSelectorHistory`
 - :py:class:`smarter.lib.journal.models.SAMJournal`

Scaling
-------

If you use Kubernetes Smarter Chatbots will scale seamlessly with demand.
See `https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/ <https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/>`__ for more information.

Troubleshooting
---------------

Beyond the Django models listed above, you should also check the smarter pod logs
for any errors. Use the following command to view the logs:

.. code-block:: bash

  kubectl logs -n <namespace> <smarter-pod-name>

for example,

.. code-block:: bash

  kubectl logs -n smarter-platform-prod smarter-68f445c866-59lmp
