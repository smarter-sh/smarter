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
    - :doc:`Smarter Plugin <../smarter-resources/smarter-plugin>`
    - :doc:`Smarter Prompt <../smarter-resources/smarter-prompt>`
    - :doc:`Smarter CLI <../smarter-framework/smarter-cli>`
    - :doc:`Smarter Chat <../smarter-framework/developer-reference/react-integration/smarter-chat>`

Usage
--------

.. code-block:: bash

  # Smarter Prompt Engineer Workbench
  curl -X POST http://localhost:9357/api/v1/llm-clients/9/chat/?session_key=e5c0368d6d7201b60f4f20c470f4b5ba36faf45e80ddbe8b04b6cf20f33167a7

  # Deployed Smarter LLMClient - Production
  curl -X GET https://stackademy.3141-5926-5359.api.example.com/chat/?session_key=<SESSION-KEY>

Example Manifest
----------------

.. literalinclude:: ../../../smarter/smarter/apps/plugin/data/stackademy/stackademy-llmclient-sql.yaml
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
 - :py:class:`smarter.apps.plugin.models.PluginSelectorHistory`
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
