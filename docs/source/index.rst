.. Smarter documentation master file, created by
   sphinx-quickstart on 2025-Nov-24.

The Smarter Project |project_version| Documentation
======================================================

.. image:: https://img.shields.io/badge/Website-smarter.sh-darkorange
   :target: https://smarter.sh
   :alt: Project Website

.. image:: https://img.shields.io/badge/Community-20%2B%20Contributors-blue?logo=github
   :target: contributors.html
   :alt: Made with ❤️ by Contributors

.. image:: https://img.shields.io/badge/Community-Discussions-blue?logo=github
   :target: https://github.com/smarter-sh/smarter/discussions
   :alt: Forums

.. image:: https://img.shields.io/badge/YouTube-Tutorials-red?logo=youtube
   :target: https://www.youtube.com/@project-smarter
   :alt: Video Tutorials

.. image:: https://img.shields.io/docker/pulls/mcdaniel0073/smarter.svg?logo=docker&label=Docker
   :target: https://hub.docker.com/r/mcdaniel0073/smarter
   :alt: DockerHub

.. image:: https://img.shields.io/endpoint?url=https://artifacthub.io/badge/repository/project-smarter
   :target: https://artifacthub.io/packages/search?repo=project-smarter
   :alt: ArtifactHub

.. image:: https://img.shields.io/badge/Contribute-Good%20First%20Issues-success?logo=github
   :target: https://github.com/smarter-sh/smarter/labels/good%20first%20issue
   :alt: Contribute

.. image:: https://img.shields.io/badge/Support-GitHub%20Sponsors-ff69b4?logo=githubsponsors
   :target: https://github.com/sponsors/lpm0073
   :alt: Donate

.. image:: https://img.shields.io/badge/License-AGPL--3.0-blue?logo=gnu
   :target: https://www.gnu.org/licenses/agpl-3.0
   :alt: AGPL-3 License


The Smarter Project is an open source, cloud-native :doc:`platform <smarter-platform>` and
:doc:`developer framework <smarter-framework>` for building sophisticated AI applications
**without writing a single line of Python**. An application that searches the web, queries your
databases, calls your APIs, uses the tools of any MCP server, and defends itself against prompt
injection and data leaks is described in one short YAML file, and deployed with one command.

.. admonition:: Quick Start: up and running on your desktop in about 10 minutes
   :class: tip

   With `Docker Desktop <https://docs.docker.com/desktop/>`__ installed:

   .. code-block:: console

      git clone https://github.com/smarter-sh/smarter-deploy.git
      cd smarter-deploy
      make            # creates a .env file. Add your credentials to it before continuing.
      make init       # pulls the Docker containers and seeds the platform with test data
      make run        # starts the platform

   Then open http://localhost:9357/login/ and log in as ``admin@smarter.sh`` with password
   ``smarter`` (change it after your first login), and install the
   `Smarter CLI <https://smarter.sh/cli>`__.

   See the :doc:`Quick Start Guide <smarter-platform/installation/quick-start>` for step-by-step
   instructions with screenshots.

No code. Just a manifest.
-------------------------

Until now, an AI application that combines retrieval, tool calling, and safety controls has been a
software project: Python code for every API client, database query, and MCP session, glue code to
route tool calls, and custom middleware to filter what goes in and out of the model. That code has
to be written, tested, secured, and maintained by engineers, and every change to the application is
a change to the code.

Smarter replaces all of it with a :doc:`Smarter Manifest (SAM) <smarter-framework/smarter-manifests>`,
a plain `YAML <https://en.wikipedia.org/wiki/YAML>`__ file that declares **what** an application is,
rather than programming **how** it works. Every :doc:`Resource <smarter-resources>` in Smarter, from an
:doc:`Account <smarter-resources/smarter-account>` to an :doc:`LLMClient <smarter-resources/smarter-llmclient>`
to a :doc:`Guardrail <smarter-resources/smarter-guardrail>`, is created the same way:

.. code-block:: console

   smarter apply -f my-ai-application.yaml

This changes who can build AI applications, and how fast:

- **No programming required.** Prompt engineers, business analysts, and product managers can build,
  read, and change production AI applications themselves. The manifest is the application.
- **Sophistication is a list, not a project.** Giving an application web search, a SQL database,
  an MCP server, or a prompt injection guardrail means adding one line to its manifest.
- **One way to do everything.** There is no resource-specific SDK to learn and no API convention to
  memorize. If you can write one manifest, you can write them all.
- **Infrastructure as code for AI.** Manifests are versioned, diffed, reviewed in pull requests, and
  deployed from CI/CD, like the rest of your infrastructure.

Every way to reach external data
--------------------------------

An LLM is only as useful as the information it can get to. Smarter connects your AI applications
to external data through every approach in use today. Each one is a :doc:`Resource <smarter-resources>`
that you declare in a manifest, and none of them requires you to write code:

- **Remote APIs**: an :doc:`API Plugin <smarter-resources/plugin/plugin/api>` calls your REST
  services, and authenticates with credentials that are stored as
  :doc:`Secrets <smarter-resources/smarter-secret>`, which the model never sees.
- **Remote SQL**: a :doc:`SQL Plugin <smarter-resources/plugin/plugin/sql>` runs parameterized
  queries against your databases through a managed :doc:`Connection <smarter-resources/smarter-connection>`.
- **MCP servers**: an :doc:`MCPClient <smarter-resources/smarter-mcpclient>` gives your application
  the tools of any server in the Model Context Protocol ecosystem.
- **The web**: a :doc:`WebsearchPlugin <smarter-resources/plugin/plugin/websearch>` searches the web
  and reads the pages it finds.
- **Expertise**: a :doc:`SkillPlugin <smarter-resources/plugin/plugin/skill>` packages instructions
  and reference material that teach a model how to do a specific job well.
- **Your own documents**: a :doc:`Vectorstore <smarter-resources/smarter-vectorstore>` provides
  semantic search over the content that you load into it.

Governed from the first prompt
------------------------------

Instructions in a system prompt are requests, not controls. A Smarter
:doc:`Guardrail <smarter-resources/smarter-guardrail>` is a deterministic software control that
inspects every message on its way to the model, and every reply on its way back. Guardrails
moderate abusive and unsafe content, redact personal data and leaked secrets, and stop
prompt injection, jailbreaks, and code injection from bad actors, whatever the model would
have done. Like everything else in Smarter, a guardrail is declared in a manifest and
added to an application by name, with no code. Every intervention is recorded, so each :doc:`Prompt <smarter-resources/smarter-prompt>`
can be traced back through the guardrail checks, tool calls, and model connection that
produced it, to the :doc:`Account <smarter-resources/smarter-account>` and budget that authorized it.

Contained by design
-------------------

There is growing concern about AI agents that go rogue: agents that run code they were never
meant to run, reach systems they were never meant to reach, and break out of the sandboxes that
were supposed to contain them. Smarter was designed from the start on the assumption that a model
will eventually try to do something it should not. It does not rely on the model to behave. It
makes the dangerous actions impossible:

- **No code execution.** Smarter never runs code written by a model, or by a third party, on its
  own servers. A :doc:`SkillPlugin <smarter-resources/plugin/plugin/skill>` provides instructions,
  not programs, and Smarter rejects any :doc:`MCPClient <smarter-resources/smarter-mcpclient>`
  that would launch an MCP server as a local process. Remote MCP servers run on their own
  infrastructure, not on yours.
- **Nowhere to escape to.** In production, Smarter runs on
  :doc:`private VPC networks <smarter-platform/security>` wherever possible, and
  `Calico <https://www.tigera.io/project-calico/>`_ network policies on Kubernetes control which
  ports and services each workload can reach. Containers run as a non-root user. A model cannot
  open a connection that the network will not carry, so breaking out is not a matter of clever
  prompting. It is not technically possible.
- **Hardened outbound requests.** When a plugin fetches a web page, it uses https on port 443
  only, to public addresses only, with every redirect validated. A model cannot direct Smarter
  to reach your internal network or your cloud provider's instance metadata.
- **Role-based access at every layer**, from Kubernetes and the cloud account, to the
  :doc:`Account <smarter-resources/smarter-account>` and user, to each individual Resource.
  A model can use only the plugins, MCP clients, and connections that its manifest names,
  and a manifest can name only the Resources that its author is permitted to use.
- **Credentials the model never holds.** API keys and passwords are stored as encrypted
  :doc:`Secrets <smarter-resources/smarter-secret>`, and are applied by the platform when it
  makes a request. They never appear in a prompt.
- **Guardrails on both sides of the model**, which stop prompt injection and jailbreaks on the way
  in, and stop leaked secrets and personal data on the way out.
- **Budgets and a complete audit trail.** Every request is authorized against the account's
  :doc:`budget <smarter-platform/cost-accounting>`, and every prompt, tool call, and guardrail
  intervention is recorded in the :doc:`Smarter Journal <smarter-framework/developer-reference/smarter-journal>`.

See :doc:`Security <smarter-platform/security>` for details.

Composed like an orchestra
--------------------------

These capabilities are designed to work together, and you conduct them from the manifest. A single
:doc:`LLMClient <smarter-resources/smarter-llmclient>` manifest combines a model from any
:doc:`provider <smarter-resources/smarter-provider>` with the plugins, MCP clients, and guardrails
that it needs, simply by listing them by name. Each piece plays its own part, and Smarter handles
the tool calling, authentication, guardrail enforcement, and auditing in between. For example, a research analyst can search
the web, read PDF reports, and have its citations checked before they reach the user. A
customer support agent can draft on-brand replies behind nine guardrails for safety and privacy.
A data analyst can answer business questions in SQL, check syntax against the database's own
documentation over MCP, and never leak personal data. When one application is not enough, an
:doc:`Orchestrator <smarter-resources/smarter-orchestrator>` coordinates several LLMClients in
sequential, parallel, supervisor/worker, routing, and voting/debate workflows, and it too is
just a manifest.

Smarter ships with built-in LLMClients like these, so that you can see the whole ensemble at work
on a fresh installation, and then copy the manifests to start your own.

Built for teams
---------------

AI applications are built by teams, not individuals, so Smarter builds ownership and sharing into
every Resource. Each LLMClient, Plugin, MCPClient, Guardrail, Secret, and Connection is owned by the
person who created it, and is shared automatically with everyone in the same
:doc:`Account <smarter-resources/smarter-account>`. Teammates can reuse each other's plugins,
MCP clients, and guardrails in their own manifests by name, without copying them, and credentials
stay in :doc:`Secrets <smarter-resources/smarter-secret>` rather than in anyone's manifest. Resources that Smarter provides are shared with every account, so
your team can start from a library of ready-made building blocks. Permissions are enforced by the
platform itself, in every query, for the :doc:`web console <smarter-platform/smarter-web-console>`,
the :doc:`REST API <smarter-framework/smarter-api>`, and the :doc:`CLI <smarter-platform/cli>`
alike, and usage is charged to the account's budget, so it is always clear who built what, who
can change it, and who is paying for it.

Runs at scale, on your infrastructure
-------------------------------------

Smarter runs wherever you do. Start with a single
`Docker <https://hub.docker.com/r/mcdaniel0073/smarter>`_ container on your laptop, then go to
production on `Kubernetes <https://kubernetes.io/>`_ with the
`Smarter Helm chart <https://artifacthub.io/packages/helm/project-smarter/smarter>`_, where the
application servers and background workers scale horizontally and automatically with demand.
The same manifests that you wrote on your laptop run unchanged in a production cluster that
serves your whole organization. There is no managed-service dependency and no vendor lock-in.
You own the deployment, the data, and the infrastructure that it runs on.

At a glance
-----------

- **Get started** | :doc:`smarter-platform/installation/quick-start` | :doc:`smarter-platform/prerequisites` | :doc:`smarter-platform/trouble-shooting` | `Tutorial <https://docs.smarter.sh/learn/>`__
- **Platform**

  - A proxy server that gives secure, governed, auditable access to AI providers and resources, without exposing secrets or the underlying vendor accounts.
  - Build every :doc:`AI resource <smarter-resources>` with declarative :doc:`YAML manifests <smarter-framework/smarter-manifests>`, with no Python programming, much as you would with `Kubernetes <https://kubernetes.io/>`_.
  - Manage resources with the :doc:`web console <smarter-platform/smarter-web-console>`, the :doc:`REST API <smarter-framework/smarter-api>`, and the :doc:`command-line interface <smarter-platform/cli>`.
  - Built for teams: every resource has an owner, and is shared with everyone in the owner's :doc:`Account <smarter-resources/smarter-account>`.
  - Runs at scale on Kubernetes, with automatic horizontal scaling of application servers and background workers.
  - Built-in :doc:`logging <smarter-framework/developer-reference/smarter-journal>`, :doc:`cost accounting <smarter-platform/cost-accounting>`, and :doc:`security <smarter-platform/security>`.

- **Knowledge and tools**

  - :doc:`API <smarter-resources/plugin/plugin/api>`, :doc:`SQL <smarter-resources/plugin/plugin/sql>`, :doc:`Websearch <smarter-resources/plugin/plugin/websearch>`, :doc:`Skill <smarter-resources/plugin/plugin/skill>`, and :doc:`Static <smarter-resources/plugin/plugin/static>` :doc:`Plugins <smarter-resources/smarter-plugin>`.
  - :doc:`MCPClients <smarter-resources/smarter-mcpclient>` for the Model Context Protocol ecosystem.
  - :doc:`Vectorstores <smarter-resources/smarter-vectorstore>` for semantic search over your own content.

- **Trust and safety**

  - Input and output :doc:`Guardrails <smarter-resources/smarter-guardrail>` for moderation, self-harm, personal data, data subject requests, leaked secrets, profanity, fabricated citations, prompt injection, jailbreaks, and code injection.
  - End-to-end audit, from each :doc:`Prompt <smarter-resources/smarter-prompt>` back to the Account that authorized it.

- **Models and workflows**

  - Works with many :doc:`AI model providers <smarter-resources/smarter-provider>`, including `OpenAI <https://developers.openai.com/api/reference/overview/>`_, `Google AI <https://ai.google.dev/api>`_, `Meta AI <https://developers.facebook.com/docs/>`_, and `DeepSeek <https://api-docs.deepseek.com/>`_, as well as self-hosted models with :doc:`LLMHost <smarter-resources/smarter-llmhost>`.
  - Multi-agent workflows with :doc:`Orchestrator <smarter-resources/smarter-orchestrator>`.
  - A :doc:`prompt engineering workbench <smarter-framework/developer-reference/react-integration/smarter-chat>` for testing applications before you deploy them.

- **Developer framework**

  - For when you do want to write code: built on :doc:`Django <smarter-framework/developer-reference/lib/django>`, :doc:`Django REST Framework <smarter-framework/developer-reference/lib/drf>`, and :doc:`Pydantic <smarter-framework/technologies/pydantic>`, and the same framework that Smarter itself is built on.
  - Automated :doc:`AWS cloud infrastructure <smarter-framework/technologies/aws>` and :doc:`Kubernetes <smarter-framework/technologies/kubernetes>` management.
  - A :doc:`React component <smarter-framework/developer-reference/react-integration/smarter-chat>` that adds a Smarter chat to any web page.
  - `Python SDK <https://pypi.org/project/smarter-api/>`_, `NPM packages <https://www.npmjs.com/package/@smarter.sh/ui-chat>`_, and a `VS Code extension <https://marketplace.visualstudio.com/items?itemName=querium.smarter-manifest>`_.


Usage
------

**1. Create a Smarter manifest**

This built-in LLMClient is a complete, governed AI application. It combines a SkillPlugin, an
MCPClient, and four guardrails, and it contains no code.

.. literalinclude:: ../../smarter/smarter/apps/llmclient/data/llm-clients/llmclient-data-analyst.yaml
   :language: yaml
   :caption: Example Smarter Manifest


**2. Apply the Manifest**

.. code-block:: console

   smarter apply -f llmclient-data-analyst.yaml

**3. Interact**

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




.. toctree::
   :maxdepth: 1
   :caption: Getting Started

   Quick Start Guide <smarter-platform/installation/quick-start>

.. toctree::
   :maxdepth: 1
   :caption: Table of Contents

   smarter-platform
   smarter-resources
   smarter-framework
   adr
   contributors

.. toctree::
   :maxdepth: 1
   :caption: External Resources

   external-links/support-smarter
   external-links/swagger
   external-links/manifest-reference
   external-links/json-schemas
   external-links/youtube
