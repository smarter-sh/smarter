Smarter LLM Client
==================

.. attention::

   The term 'LLMClient' is used interchangeably with 'Agent', 'Workflow Unit'
   and 'Harness' throughout this documentation.

Overview
--------

The Smarter LLMClient is the platform’s implementation of what is commonly
known as an LLM harness. It provides the execution environment surrounding a
large language model, managing the prompts, conversation state, tool execution,
configuration, security, and runtime behavior required to transform a foundation
model into a reliable, production-ready application.

LLMClients support both interactive conversations with human users and fully
automated workflows. In addition to orchestrating requests to a language model,
they leverage the Smarter Plugin architecture to invoke tools, retrieve data
from private systems, access external APIs, execute code, and integrate other
runtime capabilities. This allows developers to extend the model far beyond
text generation while maintaining consistent interfaces, security boundaries,
and execution policies.

Each LLMClient is defined by a YAML-based :doc:Smarter API Manifest (SAM) <../smarter-framework/smarter-api>,
which describes its model configuration, prompts, plugins, user interface,
behavior, and other runtime characteristics. Because every aspect of an
LLMClient is declaratively configured, developers can easily customize and
deploy specialized AI applications without modifying framework code.

LLMClients are managed using the :doc:`Smarter command-line interface (CLI) <../smarter-platform/cli>`.

.. seealso::

    - :doc:`Smarter API Manifest (SAM) <../smarter-framework/smarter-api>`
    - :doc:`Smarter LLMTool Plugin <../smarter-resources/smarter-llmtool>`
    - :doc:`Smarter Prompt <../smarter-resources/smarter-prompt>`
    - :doc:`Smarter CLI <../smarter-framework/smarter-cli>`
    - :doc:`Smarter Chat <../smarter-framework/smarter-chat>`

Usage
--------

A deployed LLMClient has its own host, e.g. ``https://stackademy-sql.3141-5926-5359.api.example.com``,
with two endpoints, which answer POST requests only. ``/config/`` returns the chat's configuration and
a new chat session:

.. code-block:: bash

  curl -X POST https://stackademy-sql.3141-5926-5359.api.example.com/config/ \
    -H "Content-Type: application/json"

``/prompt/`` sends a prompt, and returns the LLM's response, as JSON, whose assistant message is
Markdown:

.. code-block:: bash

  curl -X POST https://stackademy-sql.3141-5926-5359.api.example.com/prompt/ \
    -H "Content-Type: application/json" \
    -d '{"messages": [{"role": "user", "content": "What courses are there?"}]}'

To continue a chat, send the ``session_key`` that ``/config/`` returned, e.g.
``{"session_key": "<SESSION-KEY>", "messages": [...]}``, and the chat's earlier messages. An LLMClient
with api keys requires one in every request: add ``-H "Authorization: Token <YOUR-API-KEY>"``.

An LLMClient is built from other SAM resources, each declared in its own manifest: the Provider whose
models it prompts, the plugins and MCPClients that give it tools, its Guardrails, its Custom Domain and
its api key, and beneath them what those use in turn, such as Connections and Secrets. The workbench's
Console draws this tree in its Architecture tab, right of Manifest, as a card for each resource, with its
kind, its name and its owner. Clicking a card opens that resource's manifest page, where its manifest can
be edited, in a new tab. The tree is the LLMClient broker's ``dependency_tree()``: see
:doc:`Record Locators and Dependency Trees <../smarter-framework/smarter-manifests/record-locators>`.

The workbench's Console has a Deployment tab, its far right one, for what comes after
deploying: the LLMClient's status and url, where to go from here, with the integrations that put its
chat on a web site (:doc:`WordPress <../smarter-framework/smarter-wordpress>`,
:doc:`Drupal <../smarter-framework/smarter-drupal>`, :doc:`Shopify <../smarter-framework/smarter-shopify>`,
the :doc:`npm package and any html page <../smarter-framework/smarter-chat/embedding>`), how to secure
its url, these commands, how its chat sessions work, and its manifest. The tab lists the account's
:doc:`api keys <../smarter-platform/api-keys>`, creates one, showing its secret once, and attaches
it to the LLMClient, which then requires it, or detaches it. Attaching a key there is the same as
naming it in the manifest's ``spec.apiKey`` and applying it: an LLMClient has one api key, and the
others are detached. Only the LLMClient's owner or an account admin can attach a key, and only an
account admin can create one. An LLMClient that isn't deployed shows the url that it will have, and
the command that deploys it.

A platform administrator can also show that page to browsers, with the ``enable_llmclient_endpoints_page``
:doc:`waffle switch <../smarter-framework/developer-reference/lib/django/waffle>`, which is off by
default. A browser that opens a deployed LLMClient's url, or either endpoint, then receives it, with
its api key steps written out rather than as forms, the LLMClient's manifest without its owner's
username, and links to The Smarter Project. While the switch is off, a GET of an endpoint is answered
``405 Method Not Allowed``.

The workbench, and the platform's api, reach the same endpoints by the LLMClient's id, at
``/api/v1/llm-clients/<id>/config/`` and ``/api/v1/llm-clients/<id>/prompt/``, for a user who may read
the LLMClient: a logged-in user, or a request with that user's Smarter api key.
See :doc:`The Chat API Contract <../smarter-framework/smarter-chat/api-contract>`.

Web Pages That Embed It
-----------------------

A deployed LLMClient can be the chat backend of any web page, with
:doc:`Smarter Chat <../smarter-framework/smarter-chat>`, the ``@smarter.sh/ui-chat`` React component.
The page calls the LLMClient from the browser, so its origin must be allowed, in
``spec.config.prompt.allowedOrigins``:

.. code-block:: yaml

  spec:
    config:
      prompt:
        allowedOrigins:
          - https://www.example.com
          - http://localhost:5173

Each origin is a scheme, a host and an optional port, without a path or a wildcard. If the LLMClient
has an api key, the page must send one; without api keys, the LLMClient is public, and its prompts
are charged to its owner. See
:doc:`Embedding Smarter Chat <../smarter-framework/smarter-chat/embedding>`.

Styling the Chat
----------------

An LLMClient's manifest splits ``spec.config`` in two. ``prompt``, which is required, is what the
LLMClient is: its LLM provider, model and system prompt, and the words of its chat. ``styles``, which is
optional, is how its chat looks, in the workbench and on every page that embeds it: its logo, avatars,
background image, font and colors.

.. code-block:: yaml

  spec:
    config:
      prompt:
        appName: Stackademy
        appAssistant: Stanley
      styles:
        appLogoUrl: https://cdn.example.com/stackademy/logo.png
        googleFont: Nunito
        conversationHeader:
          backgroundColor: "#14213d"
          color: "#ffffff"
        outgoingMessage:
          backgroundColor: "#fca311"

No CSS or web development is needed. :doc:`Styling Your LLMClient's Chat <llmclient/styles>` explains
every setting, with a crash course in colors, sizes, fonts and images, and a case study.

.. toctree::
   :maxdepth: 1

   llmclient/styles

Example Manifest
----------------

.. literalinclude:: ../../../smarter/smarter/apps/llmclient/data/stackademy/stackademy-llmclient-sql.yaml
   :language: yaml
   :caption: Example Smarter Manifest



Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   llmclient/api
   llmclient/models
   llmclient/sam
   llmclient/serializers
   llmclient/react-ui
   llmclient/helper
   llmclient/kubernetes-ingress
   llmclient/management-commands
   llmclient/middleware
   llmclient/tasks
   llmclient/signals
   llmclient/urls
   llmclient/utils
   llmclient/views


Sandbox Mode
------------

Smarter LLMClients can be operated in a 'Sandbox Mode', which restricts their
capabilities to ensure safe experimentation and testing. In this mode, llmclient
are only addressable using URL schemes that authenticate with Django sessions.
That is, they cannot be accessed via API keys nor will they function using
URL schemas such as `stackademy.1234-5678-9012.api.example.com`.

An example sandbox mode url:

  ``https://platform.smarter.sh/workbench/stackademy-sql/chat/``



Deploying
---------

Deploy a Smarter LLMClient using the Smarter CLI. For example:

.. code-block:: bash

  smarter deploy llmclient stackademy-sql

.. code-block:: bash

  smarter deploy llmclient -h
  Deploys a LLMClient:

  smarter deploy llmclient <name> [flags]

  The Smarter API will deploy the LLMClient.

  Usage:
    smarter deploy llmclient <name> [flags]

  Flags:
    -h, --help   help for llmclient

  Global Flags:
        --api_key string         Smarter API key to use
        --config string          config file (default is $HOME/.smarter/config.yaml)
        --environment string     environment to use: local, alpha, beta, next, prod. Default is prod
    -o, --output_format string   output format: json, yaml (default "json")
    -v, --verbose                verbose output



Updating
--------

Update a Smarter LLMClient using the Smarter CLI. For example:

.. code-block:: bash

  smarter apply -f path/to/llmclient-manifest.yaml


Deleting
--------

Delete a Smarter LLMClient using the Smarter CLI. For example:

.. code-block:: bash

  smarter delete llmclient stackademy-sql


Testing
-------

Test your Smarter LLMClient using the Smarter Workbench while in Sandbox Mode.

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

Use ad hoc Sql queries to monitor your Smarter LLMClient's production performance and usage.

See:

 - :py:class:`smarter.apps.llmclient.models.LLMClientRequests`
 - :py:class:`smarter.apps.llmtool.models.PluginSelectorHistory`
 - :py:class:`smarter.lib.journal.models.SAMJournal`

Scaling
-------

If you use Kubernetes Smarter LLMClients will scale seamlessly with demand.
See `https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/ <https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/>`__ for more information.

Trouble Shooting
-----------------

Beyond the Django models listed above, you should also check the smarter pod logs
for any errors. Use the following command to view the logs:

.. code-block:: bash

  kubectl logs -n <namespace> <smarter-pod-name>

for example,

.. code-block:: bash

  kubectl logs -n smarter-platform-prod smarter-68f445c866-59lmp
