Smarter Python SDK
==================

The Smarter Python SDK is the official Python library of the :doc:`Smarter API <smarter-api>`. It is
to Smarter what the ``openai`` package is to the OpenAI API: one ``pip install`` gives your Python
software typed, complete access to your own Smarter platform, whether it runs on your laptop or on
:doc:`Kubernetes <smarter-on-kubernetes>`.

Use it to build custom software that is tightly integrated with your Smarter resources, without
customizing or forking the Smarter platform: a web application that chats with your
:doc:`LLMClients <../smarter-resources/smarter-llmclient>`, a CI/CD job that applies your
:doc:`manifests <smarter-manifests>`, a data pipeline that loads documents into a
:doc:`Vectorstore <../smarter-resources/smarter-vectorstore>`, a service that calls the tools of your
:doc:`MCP servers <../smarter-resources/smarter-mcpclient>`, or a test suite for your prompts.

.. code-block:: console

   pip install smarter-api

.. code-block:: python

   from smarter import Smarter

   client = Smarter()  # SMARTER_API_KEY, or the smarter cli's ~/.smarter/config.yaml

   llmclient = client.llm_clients.find("customer_support")
   response = client.llm_clients.prompt(llmclient.id, "Where is my order #1234?")
   print(response.text)

The package is ``smarter-api`` on `PyPI <https://pypi.org/project/smarter-api/>`__, and its import
name is ``smarter``. Its source is
`github.com/smarter-sh/smarter-python <https://github.com/smarter-sh/smarter-python>`__.


The SDK or the CLI?
-------------------

The SDK and the :doc:`Smarter CLI <smarter-cli>` manage the same resources, through the same API.
The difference is how you use them.

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Smarter Python SDK
     - Smarter CLI
   * - A Python library that you **import** into your own software.
     - A program that you **install** on your computer.
   * - ``client.manifests.apply("guardrail.yaml")``
     - ``smarter apply -f guardrail.yaml``
   * - Returns typed Pydantic models, and raises typed exceptions.
     - Prints JSON or YAML in a terminal window.
   * - For applications, services, notebooks, tests and automation.
     - For people at a keyboard, and shell scripts.

The SDK reads the CLI's configuration file, so a developer who has run ``smarter configure`` needs
no other setup.


What It Covers
--------------

- **Every resource kind**, through the same brokered :doc:`manifest API <smarter-api/cli>` that the
  CLI uses: ``apply``, ``validate``, ``get``, ``describe``, ``delete``, ``deploy``, ``undeploy`` and
  ``logs``.
- **Prompts and conversations**: prompt an LLMClient, hold a multi-turn chat that keeps its session,
  and stream a prompt's progress as it runs, exactly as :doc:`Smarter Chat <smarter-chat>` does.
- **Resource actions**: evaluate a Guardrail, call an MCP server's tools, add documents to and
  search a Vectorstore, plan and deploy an LLMHost, discover open-weight models, read the chat
  history and the :doc:`Smarter Journal <smarter-api/smarter-journal>`, and call an LLM provider
  through a Proxy.
- **The platform's own Pydantic models**: a typed model of every manifest kind, the
  :doc:`Smarter Chat API contract <smarter-chat/api-contract>`, the Smarter Journal contract and the
  :doc:`Django-React integration <developer-reference/react-integration>` contract.


Where to Start
--------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - If you want to...
     - Read
   * - Connect to your platform: api keys, urls, environments, timeouts
     - :doc:`Configuration <smarter-python/configuration>`
   * - Create, change and delete resources from Python
     - :doc:`Manifests <smarter-python/manifests>`
   * - Prompt an LLMClient, chat with it, or stream its progress
     - :doc:`Prompts and Chat <smarter-python/chat>`
   * - Use Guardrails, MCP clients, Vectorstores, LLMHosts and the other resources
     - :doc:`Resources <smarter-python/resources>`
   * - Build manifests in code, or read the API's contracts as typed models
     - :doc:`Models <smarter-python/models>`
   * - Handle errors, retries, timeouts and logging
     - :doc:`Errors and Reliability <smarter-python/errors>`
   * - Contribute to the SDK
     - :doc:`Developing the SDK <smarter-python/development>`
   * - Look up a class or method
     - :doc:`API Reference <smarter-python/reference>`


.. toctree::
   :maxdepth: 2
   :caption: Smarter Python SDK

   smarter-python/configuration
   smarter-python/manifests
   smarter-python/chat
   smarter-python/resources
   smarter-python/models
   smarter-python/errors
   smarter-python/development
   smarter-python/reference
