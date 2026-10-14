Smarter Go SDK
==============

The Smarter Go SDK is the official Go library of the :doc:`Smarter API <smarter-api>`. It is to
Smarter what ``openai-go`` is to the OpenAI API: one ``go get`` gives your Go software typed,
complete access to your own Smarter platform, whether it runs on your laptop or on
:doc:`Kubernetes <smarter-on-kubernetes>`.

Use it to build custom software that is tightly integrated with your Smarter resources, without
customizing or forking the Smarter platform: a service that chats with your
:doc:`LLMClients <../smarter-resources/smarter-llmclient>`, a Kubernetes operator or CI/CD job that
applies your :doc:`manifests <smarter-manifests>`, a pipeline that loads documents into a
:doc:`Vectorstore <../smarter-resources/smarter-vectorstore>`, or a tool that calls the tools of
your :doc:`MCP servers <../smarter-resources/smarter-mcpclient>`.

.. code-block:: console

   go get github.com/smarter-sh/smarter-golang

.. code-block:: go

   client, err := smarter.NewClient() // SMARTER_API_KEY, or the smarter cli's ~/.smarter/config.yaml
   if err != nil {
       log.Fatal(err)
   }
   ctx := context.Background()
   llmclient, err := client.LLMClients.Find(ctx, "customer_support")
   if err != nil {
       log.Fatal(err)
   }
   response, err := client.LLMClients.Prompt(ctx, llmclient.Ref(), smarter.Text("Where is my order #1234?"), nil)
   if err != nil {
       log.Fatal(err)
   }
   fmt.Println(response.Text())

The module is ``github.com/smarter-sh/smarter-golang``, and its package is ``smarter``. Its API
reference is on `pkg.go.dev <https://pkg.go.dev/github.com/smarter-sh/smarter-golang>`__, with
runnable examples, and its source is
`github.com/smarter-sh/smarter-golang <https://github.com/smarter-sh/smarter-golang>`__. It supports
the Go releases that the Go team supports.

It has the same features as the :doc:`Smarter Python SDK <smarter-python>`, which is the reference
implementation of every Smarter SDK: the same resources, the same verbs and the same errors, with Go
names (``client.LLMClients``, ``ExampleManifest``), a ``context.Context`` on every call, and errors
for ``errors.Is`` and ``errors.As``.


The SDK or the CLI?
-------------------

The SDK and the :doc:`Smarter CLI <smarter-cli>` manage the same resources, through the same API,
and both are written in Go. The difference is how you use them.

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Smarter Go SDK
     - Smarter CLI
   * - A library that you **import** into your own software.
     - A program that you **install** on your computer.
   * - ``client.Manifests.Apply(ctx, manifest)``
     - ``smarter apply -f guardrail.yaml``
   * - Returns typed structs, and errors for ``errors.Is`` and ``errors.As``.
     - Prints JSON or YAML in a terminal window.
   * - For services, operators, tests and automation.
     - For people at a keyboard, and shell scripts.

The SDK reads the CLI's configuration file exactly as the CLI does, so a developer who has run
``smarter configure`` needs no other setup.


What It Covers
--------------

- **Every resource kind**, through the same brokered :doc:`manifest API <smarter-api/cli>` that the
  CLI uses: ``Apply``, ``Validate``, ``Get``, ``Describe``, ``Delete``, ``Deploy``, ``Undeploy`` and
  ``Logs``.
- **Prompts and conversations**: prompt an LLMClient, hold a multi-turn chat that keeps its session,
  and stream a prompt's progress as it runs, exactly as :doc:`Smarter Chat <smarter-chat>` does.
- **Resource actions**: evaluate a Guardrail, call an MCP server's tools, add documents to and
  search a Vectorstore, plan and deploy an LLMHost, discover open-weight models, read the chat
  history and the :doc:`Smarter Journal <smarter-api/smarter-journal>`, and call an LLM provider
  through a Proxy.
- **The platform's own models**: a Go struct of every manifest kind, in the ``sam`` package,
  generated from the platform's JSON Schemas, and the
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
     - :doc:`Configuration <smarter-golang/configuration>`
   * - Create, change and delete resources from Go
     - :doc:`Manifests <smarter-golang/manifests>`
   * - Prompt an LLMClient, chat with it, or stream its progress
     - :doc:`Prompts and Chat <smarter-golang/chat>`
   * - Use Guardrails, MCP clients, Vectorstores, LLMHosts and the other resources
     - :doc:`Resources <smarter-golang/resources>`
   * - Build manifests in code, or read the API's contracts as structs
     - :doc:`Models <smarter-golang/models>`
   * - Handle errors, retries, timeouts, cancellation and logging
     - :doc:`Errors and Reliability <smarter-golang/errors>`
   * - Contribute to the SDK
     - :doc:`Developing the SDK <smarter-golang/development>`
   * - Look up a type or method
     - `pkg.go.dev <https://pkg.go.dev/github.com/smarter-sh/smarter-golang>`__


.. toctree::
   :maxdepth: 2
   :caption: Smarter Go SDK

   smarter-golang/configuration
   smarter-golang/manifests
   smarter-golang/chat
   smarter-golang/resources
   smarter-golang/models
   smarter-golang/errors
   smarter-golang/development
