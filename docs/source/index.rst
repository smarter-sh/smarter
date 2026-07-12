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
:doc:`developer framework <smarter-framework>` for building, deploying, and governing AI
applications. It runs wherever you do — a single `Docker <https://hub.docker.com/r/mcdaniel0073/smarter>`_
container to get started, or natively on `Kubernetes <https://kubernetes.io/>`_ via the
`Smarter Helm chart <https://artifacthub.io/packages/helm/project-smarter/smarter>`_ for
production. There's no managed-service dependency and no vendor lock-in: you own the deployment,
the data, and the infrastructure it runs on.

Every capability in Smarter — from calling a model, to running a tool, to storing a credential —
is expressed as a declarative :doc:`Resource <smarter-resources>`, and every Resource is created
and managed the same way: by applying a :doc:`Smarter Manifest (SAM) <smarter-framework/smarter-manifests>`,
a plain `YAML <https://en.wikipedia.org/wiki/YAML>`__ file that declares its desired state. There's
no resource-specific SDK to learn and no separate API convention to memorize — an
:doc:`Account <smarter-resources/smarter-account>`, a :doc:`Secret <smarter-resources/smarter-secret>`,
an :doc:`LLMClient <smarter-resources/smarter-llmclient>`, an
:doc:`Orchestrator <smarter-resources/smarter-orchestrator>` coordinating a multi-agent workflow, a
:doc:`Plugin <smarter-resources/smarter-plugin>` reaching into an external database — all of it is
created, versioned, diffed, and reviewed like any other infrastructure-as-code. Because SAM files
are plain, human-readable YAML, they can be understood by non-developers — business analysts and
product managers — not just by the engineers who apply them.

Resources compose into four layers — Access & Governance, Model Connectivity, Extensibility &
Trust, and Conversation (see the full :doc:`Resource Reference <smarter-resources>`) — so a single
:doc:`Prompt <smarter-resources/smarter-prompt>` can be traced end to end: back through the
guardrail checks, tool calls, and model connection that produced it, back through any
:doc:`Orchestrator <smarter-resources/smarter-orchestrator>` run that coordinated it, to the
account and budget that authorized it in the first place. This layered, fully auditable design is
what lets Smarter scale from a single AI assistant to large, governed, multi-agent applications
without changing how you work with it.

The project combines three complementary capabilities. The
:doc:`Smarter Platform <smarter-platform>` provides :doc:`authoring & administration <smarter-platform/smarter-web-console>`,
deployment, operations, and governance. :doc:`Smarter Resources <smarter-resources>`
define the building blocks of AI applications, including :doc:`LLM providers <smarter-resources/smarter-provider>`,
:doc:`prompts <smarter-resources/smarter-prompt>`, :doc:`agents <smarter-resources/smarter-llmclient>`,
:doc:`orchestrators <smarter-resources/smarter-orchestrator>`, :doc:`plugins <smarter-resources/smarter-plugin>`,
:doc:`connections <smarter-resources/smarter-connection>`, :doc:`secrets <smarter-resources/smarter-secret>`,
vectorstores, and :doc:`integrations <smarter-resources/smarter-connection>`. The
:doc:`Smarter Development Framework <smarter-framework>` — the same framework Smarter itself is
built on and ships as open source — provides APIs, `SDKs <https://github.com/smarter-sh/smarter-python>`_,
:doc:`command-line tools <smarter-platform/cli>`, :doc:`React components <smarter-framework/developer-reference/react-integration>`,
and :doc:`developer tooling <smarter-framework/developer-reference>` for building
enterprise AI applications on top of the platform.

Whether you are deploying a single AI assistant, integrating AI into existing
business systems, or building large-scale multi-agent applications, Smarter
provides a unified framework for managing AI resources throughout their entire
lifecycle.

- **From scratch** | :doc:`smarter-platform/installation/quick-start` | :doc:`smarter-platform/prerequisites` | :doc:`smarter-platform/trouble-shooting` | `Tutorial <https://docs.smarter.sh/learn/>`__
- **Platform**

  - A proxy server that facilitates secure, governed, auditable access to AI providers and resources without exposing secrets or direct access to the underlying vendor accounts.
  - Helps you manage all your :doc:`AI resources <smarter-resources>` using easy :doc:`YAML files <smarter-framework/smarter-manifests>` (like how `Kubernetes <https://kubernetes.io/>`_ works).
  - Simple `Docker <https://hub.docker.com/r/mcdaniel0073/smarter>`_ installation. Run on Kubernetes with the `Smarter Helm chart <https://artifacthub.io/packages/helm/project-smarter/smarter>`_.
  - Manage AI resources with the :doc:`web dashboard <smarter-framework/developer-reference/react-integration/smarter-chat>`, the :doc:`REST API <smarter-framework/smarter-api>`, and the :doc:`command-line interface <smarter-platform/cli>`.
  - Keeps track of :doc:`logs <smarter-framework/developer-reference/smarter-journal>`, safety checks, :doc:`costs <smarter-platform/cost-accounting>`, and :doc:`security <smarter-platform/security>` so nothing gets lost or misused.

- **AI Resource Management**

  - Works with many :doc:`AI model providers <smarter-resources/smarter-provider>` — `OpenAI <https://developers.openai.com/api/reference/overview/>`_, `Google AI <https://ai.google.dev/api>`_, `Meta AI <https://developers.facebook.com/docs/>`_, `DeepSeek <https://api-docs.deepseek.com/>`_, and others — or self-hosted models you deploy and manage yourself.
  - Lets you :doc:`organize <smarter-resources/smarter-llmclient>` and version your prompts, and see how they change over time.
  - Coordinates multiple models into multi-agent workflows with :doc:`Orchestrator <smarter-resources/smarter-orchestrator>` — sequential, parallel, supervisor/worker, routing, and voting/debate strategies — so you can build bigger, smarter tasks.
  - Secure integrations to :doc:`external data sources <smarter-resources/smarter-plugin>` like :doc:`databases <smarter-resources/plugin/plugin/sql>` and :doc:`APIs <smarter-resources/plugin/plugin/api>`.

- **Developer Application Framework**

  - Built on :doc:`Django <smarter-framework/developer-reference/lib/django>`, :doc:`Django REST Framework <smarter-framework/developer-reference/lib/drf>`, :doc:`Pydantic <smarter-framework/technologies/pydantic>`.
  - Automated :doc:`AWS cloud infrastructure <smarter-framework/technologies/aws>` and :doc:`Kubernetes <smarter-framework/technologies/kubernetes>` management.
  - ReactJS component-based :doc:`UI integration solution <smarter-framework/developer-reference/react-integration/smarter-chat>` that works for any web page.
  - Build AI tools that connect to enterprise resources like :doc:`Sql databases <smarter-resources/plugin/plugin/sql>` and :doc:`REST APIs <smarter-resources/plugin/plugin/api>`.
  - :doc:`Prompt engineer workbench <smarter-framework/developer-reference/react-integration/smarter-chat>` for testing prompts and workflows before you deploy.
  - Vibrant developer community: `PyPI <https://pypi.org/project/smarter-api/>`_, `NPM <https://www.npmjs.com/package/@smarter.sh/ui-chat>`_, `VS Code extensions <https://marketplace.visualstudio.com/items?itemName=querium.smarter-manifest>`_, and more.


Usage
------

**1. Create a Smarter manifest**

.. literalinclude:: ../../smarter/smarter/apps/plugin/data/stackademy/stackademy-llmclient-sql.yaml
   :language: yaml
   :caption: Example Smarter Manifest


**2. Apply the Manifest**

.. code-block:: console

   smarter apply -f stackademy-llmclient-sql.yaml

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
