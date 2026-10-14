Smarter Node.js SDK
===================

The Smarter Node.js SDK is the official JavaScript and TypeScript library of the
:doc:`Smarter API <smarter-api>`. It is to Smarter what the ``openai`` package is to the OpenAI API:
one ``npm install`` gives your Node.js software typed, complete access to your own Smarter platform,
whether it runs on your laptop or on :doc:`Kubernetes <smarter-on-kubernetes>`.

Use it to build custom software that is tightly integrated with your Smarter resources, without
customizing or forking the Smarter platform: a web back end that chats with your
:doc:`LLMClients <../smarter-resources/smarter-llmclient>`, a CI/CD job that applies your
:doc:`manifests <smarter-manifests>`, a serverless function that loads documents into a
:doc:`Vectorstore <../smarter-resources/smarter-vectorstore>`, or a service that calls the tools of
your :doc:`MCP servers <../smarter-resources/smarter-mcpclient>`.

.. code-block:: console

   npm install smarter-api

.. code-block:: typescript

   import { Smarter } from "smarter-api";

   const client = new Smarter(); // SMARTER_API_KEY, or the smarter cli's ~/.smarter/config.yaml

   const llmclient = await client.llmClients.find("customer_support");
   const response = await client.llmClients.prompt(llmclient.id, "Where is my order #1234?");
   console.log(response.text);

The package is ``smarter-api`` on `npm <https://www.npmjs.com/package/smarter-api>`__, the same name
as the Python SDK's package on PyPI. It is written in TypeScript, ships its type declarations, and
runs on every Node.js release that is not end-of-life (22 and later). Its source is
`github.com/smarter-sh/smarter-nodejs <https://github.com/smarter-sh/smarter-nodejs>`__.

It has the same features as the :doc:`Smarter Python SDK <smarter-python>`, which is the reference
implementation of every Smarter SDK: the same resources, the same verbs and the same errors, with
camelCase names (``client.llmClients``, ``exampleManifest()``), promises, and ``for await`` streams.


The SDK or the CLI?
-------------------

The SDK and the :doc:`Smarter CLI <smarter-cli>` manage the same resources, through the same API.
The difference is how you use them.

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Smarter Node.js SDK
     - Smarter CLI
   * - A library that you **import** into your own software.
     - A program that you **install** on your computer.
   * - ``await client.manifests.apply("guardrail.yaml")``
     - ``smarter apply -f guardrail.yaml``
   * - Returns typed, validated objects, and throws typed errors.
     - Prints JSON or YAML in a terminal window.
   * - For applications, services, serverless functions, tests and automation.
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
- **The platform's own models**: a TypeScript type of every manifest kind, generated from the
  platform's JSON Schemas, and Zod schemas of the
  :doc:`Smarter Chat API contract <smarter-chat/api-contract>`, the Smarter Journal contract, the
  :doc:`Django-React integration <developer-reference/react-integration>` contract and every REST
  response.


Where to Start
--------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - If you want to...
     - Read
   * - Connect to your platform: api keys, urls, environments, timeouts
     - :doc:`Configuration <smarter-nodejs/configuration>`
   * - Create, change and delete resources from Node.js
     - :doc:`Manifests <smarter-nodejs/manifests>`
   * - Prompt an LLMClient, chat with it, or stream its progress
     - :doc:`Prompts and Chat <smarter-nodejs/chat>`
   * - Use Guardrails, MCP clients, Vectorstores, LLMHosts and the other resources
     - :doc:`Resources <smarter-nodejs/resources>`
   * - Build manifests in code, or read the API's contracts as typed objects
     - :doc:`Models <smarter-nodejs/models>`
   * - Handle errors, retries, timeouts, cancellation and logging
     - :doc:`Errors and Reliability <smarter-nodejs/errors>`
   * - Contribute to the SDK
     - :doc:`Developing the SDK <smarter-nodejs/development>`
   * - Look up a class or method
     - :doc:`API Reference <smarter-nodejs/reference>`


.. toctree::
   :maxdepth: 2
   :caption: Smarter Node.js SDK

   smarter-nodejs/configuration
   smarter-nodejs/manifests
   smarter-nodejs/chat
   smarter-nodejs/resources
   smarter-nodejs/models
   smarter-nodejs/errors
   smarter-nodejs/development
   smarter-nodejs/reference
