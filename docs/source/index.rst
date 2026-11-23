.. Smarter documentation master file, created by
   sphinx-quickstart on 2025-Nov-24.

The Smarter Project Documentation
=================================

Everything you need to know about Smarter |smarter-version|.

Smarter is an open source platform for building governed, production AI applications **without
writing code**: an application that searches the web, queries your databases, calls your APIs,
uses any MCP server and defends itself against prompt injection is created with one short
YAML manifest. Smarter is also a complete **platform for teaching AI**, with
:doc:`23 ready-to-teach courses <smarter-instructors/example-courses/index>` for corporate
training, universities and bootcamps.

.. admonition:: Quick Start: up and running on your desktop in about 10 minutes
   :class: tip

   With `make <https://www.youtube.com/watch?v=j5gJJe_0zP4>`__ and `Docker Desktop <https://docs.docker.com/desktop/>`__ installed:

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
   instructions with screenshots, or watch `Up and Running in Less Than 10 Minutes
   <https://youtu.be/El8L6zgGyRU>`__, which follows the same steps.

First steps
-----------

Are you new to Smarter? This is the place to start.

- **From scratch:** :doc:`Why Smarter <smarter-overview>` | :doc:`Prerequisites <smarter-platform/prerequisites>` | :doc:`Quick Start <smarter-platform/installation/quick-start>`
- **Tutorial, Your First AI Application:** `Part 1: A chatbot in the workbench <https://blog.smarter.sh/2026/11/23/first-ai-application-part-1-workbench/>`__ | `Part 2: The YAML manifest <https://blog.smarter.sh/2026/11/23/first-ai-application-part-2-yaml-manifest/>`__ | `Part 3: Calling a REST API <https://blog.smarter.sh/2026/11/23/first-ai-application-part-3-rest-api/>`__ | `Part 4: Querying a SQL database <https://blog.smarter.sh/2026/11/23/first-ai-application-part-4-sql-database/>`__ | `Part 5: Guardrails <https://blog.smarter.sh/2026/11/23/first-ai-application-part-5-guardrails/>`__
- **Advanced tutorials:** `Build a Smarter Extension in Python <https://blog.smarter.sh/2026/11/01/smarter-extension-cookiecutter-how-to/>`__
- **More tutorials:** `Tutorials on the Smarter blog <https://blog.smarter.sh/category/tutorials/>`__ | :doc:`Video tutorials <external-links/youtube>`
- **Teaching AI:** :doc:`Instructor Guide <smarter-instructor>` | :doc:`Free Course Catalog <smarter-instructors/example-courses/index>`

Getting help
------------

Having trouble? We'd like to help.

- Try :doc:`Trouble Shooting <smarter-platform/trouble-shooting>`, which has answers to many
  common problems.
- Looking for specific information? Try the :ref:`genindex` or the :ref:`modindex`.
- Ask the community, or the @Smarter Developer bot, on :doc:`Slack <slack>`, or in
  `GitHub Discussions <https://github.com/smarter-sh/smarter/discussions>`__.
- Report bugs in Smarter in the `issue tracker <https://github.com/smarter-sh/smarter/issues>`__.

How the documentation is organized
----------------------------------

Smarter has a lot of documentation, organized by who it is written for. Knowing the parts will
help you find what you need:

- The :doc:`Platform Administration Guide <smarter-platform>` covers installing, configuring,
  securing and operating a Smarter platform, on a laptop or on Kubernetes.
- :doc:`Resources <smarter-resources>` has one page for each kind of resource that a manifest can
  declare, such as an LLMClient, a Plugin or a Guardrail: what it is for, a complete example
  manifest, and its technical reference.
- The :doc:`Developer Framework <smarter-framework>` is for programmers: the APIs, SDKs and
  integrations, extending Smarter with your own tools, and developing Smarter itself.
- The :doc:`Instructor Guide <smarter-instructor>` and the
  :doc:`Free Course Catalog <smarter-instructors/example-courses/index>` are for trainers,
  teachers and the people who run a training program.
- Tutorials, which take you by the hand through building something, are published on
  `the Smarter blog <https://blog.smarter.sh/category/tutorials/>`__. Start with
  `Your First AI Application <https://blog.smarter.sh/2026/11/23/first-ai-application-part-1-workbench/>`__,
  which builds one application, a course advisor, part by part. The
  :doc:`case studies <case-studies/index>` follow real problems all the way to a working
  solution.

Teaching and training
---------------------

Smarter gives a training program a real platform to teach on, and a library of courses to teach
with, for every employee from non-programmers to platform engineers:

- **Courses:** :doc:`Free Course Catalog <smarter-instructors/example-courses/index>` | :doc:`Micro courses <smarter-instructors/example-courses/micro-courses>` | :doc:`Master classes <smarter-instructors/example-courses/master-classes>` | :doc:`Course formats <smarter-instructors/example-courses/micro-courses/course-formats>`
- **Running a class:** :doc:`Instructor Guide <smarter-instructor>` | :doc:`Accounts for cohorts <smarter-resources/smarter-account>` | :doc:`Budgets for learners <smarter-resources/smarter-budget>`
- **In practice:** :doc:`Case studies <case-studies/index>` | :ref:`AI training for your whole workforce <ai-training-courses>`

Manifests
---------

Every resource in Smarter is declared in a Smarter Application Manifest (SAM), a YAML file that
says **what** an application is, and applied with one command:

- **The basics:** :doc:`Smarter manifests <smarter-framework/smarter-manifests>` | :doc:`Example manifests <smarter-framework/smarter-manifests/example-manifests>` | :doc:`Manifest templates <smarter-framework/smarter-manifests/manifest-templates>`
- **Reference:** :doc:`JSON Schemas <external-links/json-schemas>` | :doc:`Manifest examples <external-links/manifest-reference>` | :doc:`Pydantic models <smarter-framework/smarter-manifests/pydantic-models>` | :doc:`Validation <smarter-framework/smarter-manifests/validation-strategy>`
- **Under the hood:** :doc:`The broker model <smarter-framework/smarter-broker-model>` | :doc:`Error handling <smarter-framework/smarter-manifests/error-handling>`

AI applications
---------------

An LLMClient combines a model from any provider with the tools and guardrails it needs, by name:

- **LLMClients:** :doc:`LLMClient <smarter-resources/smarter-llmclient>` | :doc:`Providers <smarter-resources/smarter-provider>` | :doc:`Prompts <smarter-resources/smarter-prompt>` | :doc:`Prompt engineering workbench <smarter-framework/smarter-chat>`
- **Workflows:** :doc:`Orchestrator <smarter-resources/smarter-orchestrator>`
- **Your own models:** :doc:`LLMHost <smarter-resources/smarter-llmhost>` | :doc:`Adding an LLM provider <smarter-platform/system-administration/llm-providers-and-extensions/adding-an-llm-provider>`
- **Your own domain:** :doc:`Custom Domain <smarter-resources/smarter-custom-domain>`

Knowledge and tools
-------------------

An LLM is only as useful as the information it can get to. Smarter connects your applications to
it, with no code:

- **Plugins:** :doc:`Overview <smarter-resources/smarter-llmtool>` | :doc:`API <smarter-resources/llmtool/plugin/api>` | :doc:`SQL <smarter-resources/llmtool/plugin/sql>` | :doc:`Websearch <smarter-resources/llmtool/plugin/websearch>` | :doc:`Skill <smarter-resources/llmtool/plugin/skill>` | :doc:`Static <smarter-resources/llmtool/plugin/static>`
- **MCP:** :doc:`MCPClient <smarter-resources/smarter-mcpclient>`
- **Your data:** :doc:`Connection <smarter-resources/smarter-connection>` | :doc:`Vectorstore <smarter-resources/smarter-vectorstore>` | :doc:`Vector search <smarter-resources/smarter-vectorsearch>`
- **Extensions:** :doc:`Overview <smarter-framework/smarter-extensions>` | :doc:`Developer guide <smarter-framework/extensions/developer-guide>` | :doc:`Testing <smarter-framework/extensions/testing>` | :doc:`Publishing <smarter-framework/extensions/publishing>` | :doc:`Lifecycle <smarter-framework/extensions/lifecycle>`

Trust, safety and cost
----------------------

Smarter does not rely on the model to behave. Every message to a model, and every reply, passes
through controls that you declare in a manifest, and every token is charged to someone:

- **Controls:** :doc:`Guardrail <smarter-resources/smarter-guardrail>` | :doc:`Secret <smarter-resources/smarter-secret>` | :doc:`Proxy <smarter-resources/smarter-proxy>`
- **Spending:** :doc:`Budget <smarter-resources/smarter-budget>` | :doc:`Cost accounting <smarter-platform/system-administration/costs-and-auditing/cost-accounting>`
- **Audit:** :doc:`The Smarter Journal <smarter-platform/system-administration/costs-and-auditing/smarter-journal>` | :doc:`Costs and auditing <smarter-platform/system-administration/costs-and-auditing>`
- **Security:** :doc:`Overview <smarter-platform/system-administration/security>` | :doc:`Security FAQ <smarter-platform/system-administration/security/security-faq>`

Accounts and teams
------------------

Every resource has an owner, and is shared with everyone in the owner's account:

- **Accounts:** :doc:`Account <smarter-resources/smarter-account>` | :doc:`Accounts and access <smarter-platform/system-administration/accounts-and-access>` | :doc:`Account management <smarter-platform/system-administration/accounts-and-access/account-management>`
- **People and keys:** :doc:`User management <smarter-platform/system-administration/accounts-and-access/user-management>` | :doc:`API keys <smarter-platform/system-administration/accounts-and-access/api-keys>` | :doc:`AuthToken <smarter-resources/smarter-authtoken>`

Interfaces
----------

Everything you can do in the web console, your own software can do too:

- **Tools:** :doc:`Web console <smarter-platform/system-administration/tools/smarter-web-console>` | :doc:`CLI <smarter-framework/smarter-cli>` | :doc:`VS Code extension <smarter-framework/vs-code-extension>` | :doc:`Django admin <smarter-platform/system-administration/tools/django-admin>`
- **The API:** :doc:`Smarter API <smarter-framework/smarter-api>` | :doc:`Authentication <smarter-framework/smarter-api/authentication>` | :doc:`Chat API <smarter-framework/smarter-api/chat>` | :doc:`OpenAPI contract <smarter-framework/smarter-openapi>` | :doc:`API reference <external-links/openapi>`
- **SDKs:** :doc:`Overview <smarter-framework/apis-and-sdks>` | :doc:`Python <smarter-framework/smarter-sdks/smarter-python>` | :doc:`Node.js <smarter-framework/smarter-sdks/smarter-nodejs>` | :doc:`Go <smarter-framework/smarter-sdks/smarter-golang>`
- **Chat on your site:** :doc:`React component <smarter-framework/smarter-chat/embedding>` | :doc:`WordPress <smarter-framework/smarter-integrations/smarter-wordpress>` | :doc:`Drupal <smarter-framework/smarter-integrations/smarter-drupal>` | :doc:`Shopify <smarter-framework/smarter-integrations/smarter-shopify>` | :doc:`Google Tag Manager <smarter-framework/smarter-integrations/smarter-gtm>` | :doc:`Documentation sites <smarter-framework/smarter-integrations/smarter-docs-sites>`

Installation and operations
---------------------------

Smarter runs wherever you do, from one Docker container on a laptop to a Kubernetes cluster that
serves your whole organization:

- **Install:** :doc:`Overview <smarter-platform/installation>` | :doc:`Quick Start <smarter-platform/installation/quick-start>` | :doc:`Developer installation <smarter-platform/installation/developer-installation>` | :doc:`Production deployment <smarter-platform/installation/production-deployment>`
- **Configure:** :doc:`Configuration <smarter-platform/configuration>` | :doc:`Overrides <smarter-platform/overrides>` | :doc:`Cloud infrastructure <smarter-platform/cloud-infrastructure>` | :doc:`URL patterns <smarter-platform/url-patterns>`
- **Operate:** :doc:`System administration <smarter-platform/system-administration>` | :doc:`Updates <smarter-platform/system-administration/operations/updates>` | :doc:`Backup and restore <smarter-platform/system-administration/operations/backup-and-restore>` | :doc:`Smarter on Kubernetes <smarter-framework/smarter-on-kubernetes>` | :doc:`Trouble Shooting <smarter-platform/trouble-shooting>`
- **MCP servers:** :doc:`Operations MCP server <smarter-platform/smarter-operations-mcp-server>` | :doc:`Project MCP server <smarter-platform/smarter-project-mcp-server>`

The developer framework
-----------------------

For when you do want to write code: Smarter is built on Django, Django REST Framework and
Pydantic, and its framework is yours to build on:

- **Start here:** :doc:`Getting started <smarter-framework/getting-started>` | :doc:`Architecture <smarter-framework/architecture>` | :doc:`Extensibility <smarter-framework/extensibility>`
- **Reference:** :doc:`Developer reference <smarter-framework/developer-reference>` | :doc:`Django <smarter-framework/developer-reference/lib/django>` | :doc:`DRF <smarter-framework/developer-reference/lib/drf>` | :doc:`Settings <smarter-framework/developer-reference/smarter-settings>`
- **Technologies:** :doc:`Overview <smarter-framework/technologies>` | :doc:`Python <smarter-framework/technologies/python>` | :doc:`Pydantic <smarter-framework/technologies/pydantic>` | :doc:`Docker <smarter-framework/technologies/docker>` | :doc:`Kubernetes <smarter-framework/technologies/kubernetes>` | :doc:`AWS <smarter-framework/technologies/aws>`

The Smarter open-source project
-------------------------------

Learn how Smarter itself is developed, and how you can contribute:

- **Community:** :doc:`Contributing <smarter-framework/guides/contributing>` | :doc:`Code of conduct <smarter-framework/guides/code-of-conduct>` | :doc:`Contributors <contributors>` | :doc:`Slack <slack>` | :doc:`Support Smarter <external-links/support-smarter>`
- **How it's built:** :doc:`Developer guidelines <smarter-framework/guides/developer-guidelines>` | :doc:`Feature checklist <smarter-framework/guides/developer-feature-checklist>` | :doc:`Documentation <smarter-framework/guides/documentation>` | :doc:`Developing with Claude Code <smarter-framework/guides/claude-code>`
- **Design decisions:** :doc:`Architecture Decision Records <adr>` | :doc:`12-factor app <smarter-framework/guides/12-factor-app>`
- **Smarter over time:** :doc:`Semantic versioning <smarter-framework/guides/semantic-versioning>` | `Release notes <https://github.com/smarter-sh/smarter/blob/main/CHANGELOG.md>`__ | `Release announcements <https://blog.smarter.sh/>`__

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Getting Started

   smarter-overview

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Teaching and Training

   smarter-instructor
   smarter-instructors/example-courses/index
   case-studies/index

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Community

   slack

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Smarter Docs

   smarter-platform
   smarter-resources
   smarter-framework
   adr
   contributors

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: External Resources

   external-links/support-smarter
   external-links/openapi
   external-links/manifest-reference
   external-links/json-schemas
   external-links/youtube
