.. Smarter documentation master file, created by
   sphinx-quickstart on Mon Nov 24 20:56:57 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Smarter |project_version| Documentation
=========================================

.. image:: https://img.shields.io/badge/Website-smarter.sh-darkorange
   :target: https://smarter.sh
   :alt: Project Website

.. image:: https://img.shields.io/badge/Donate-GitHub_Sponsors-ff69b4
   :target: https://github.com/sponsors/lpm0073
   :alt: Donate

.. image:: https://img.shields.io/badge/Forums-Discussion-blue
   :target: https://github.com/smarter-sh/smarter/discussions
   :alt: Forums

.. image:: https://img.shields.io/docker/pulls/mcdaniel0073/smarter.svg?logo=docker&label=DockerHub
   :target: https://hub.docker.com/r/mcdaniel0073/smarter
   :alt: DockerHub

.. image:: https://img.shields.io/endpoint?url=https://artifacthub.io/badge/repository/project-smarter
   :target: https://artifacthub.io/packages/search?repo=project-smarter
   :alt: ArtifactHub

.. image:: https://img.shields.io/badge/License-AGPL_v3-blue.svg
   :target: https://www.gnu.org/licenses/agpl-3.0
   :alt: AGPL-3 License

The Smarter Project is a cloud-native :doc:`platform <smarter-platform>` and
:doc:`developer framework <smarter-framework>` for
building, deploying, and managing AI applications. Using declarative
:doc:`Smarter Manifests <smarter-framework/smarter-manifests>`, developers can
define :doc:`AI resources <smarter-resources>`, :doc:`prompts <smarter-resources/smarter-prompt>`,
workflows, :doc:`agents <smarter-resources/smarter-chatbot>`, :doc:`APIs <smarter-framework/smarter-api>`,
and :doc:`integrations <smarter-resources/smarter-connection>` as version-controlled infrastructure, enabling repeatable
deployments, governance, and lifecycle management across environments.

At the center of the platform is :doc:`declarative AI <smarter-resources>`
resource management. Rather than manually configuring providers, prompts,
APIs, databases, workflows, and deployment settings across multiple systems,
developers describe their desired state in :doc:`YAML manifests <smarter-framework/smarter-manifests>`. Smarter handles
resource provisioning, dependency
management, versioning, governance, security, budget controls, and lifecycle operations, allowing
teams to focus on building solutions instead of managing infrastructure,
budgets, and operations.

The project combines three complementary capabilities. The
:doc:`Smarter Platform <smarter-platform>` provides :doc:`authoring & administration <smarter-platform/smarter-web-console>`,
deployment, operations, and governance. :doc:`Smarter Resources <smarter-resources>`
define the building blocks of AI applications, including :doc:`LLM providers <smarter-resources/smarter-provider>`,
:doc:`prompts <smarter-resources/smarter-prompt>`, :doc:`agents <smarter-resources/smarter-chatbot>`,
:doc:`plugins <smarter-resources/smarter-plugin>`, :doc:`connections <smarter-resources/smarter-connection>`,
:doc:`secrets <smarter-resources/smarter-secret>`, workflows, vectorstores,
and :doc:`integrations <smarter-resources/smarter-connection>`. The
:doc:`Smarter Development Framework <smarter-framework>` provides APIs, `SDKs <https://github.com/smarter-sh/smarter-python>`_,
:doc:`command-line tools <smarter-platform/cli>`, :doc:`React components <smarter-framework/developer-reference/react-integration>`,
and :doc:`developer tooling <smarter-framework/developer-reference>` for building
enterprise AI applications on top of the platform.

Whether you are deploying a single AI assistant, integrating AI into existing
business systems, or building large-scale multi-agent applications, Smarter
provides a unified framework for managing AI resources throughout their entire
lifecycle.

- **From scratch** | :doc:`smarter-platform/installation/quick-start` | :doc:`smarter-platform/prerequisites` | :doc:`smarter-platform/trouble-shooting` | `Tutorial <https://platform.smarter.sh/docs/learn/>`__
- **Platform**

  - A proxy server that facilitates secure, governed, auditable access to AI providers and resources without exposing secrets or direct access to the underlying vendor accounts.
  - Helps you manage all your :doc:`AI resources <smarter-resources>` using easy :doc:`YAML files <smarter-framework/smarter-manifests>` (like how `Kubernetes <https://kubernetes.io/>`_ works).
  - Simple `Docker <https://hub.docker.com/r/mcdaniel0073/smarter>`_ installation. Run on Kubernetes with the `Smarter Helm chart <https://artifacthub.io/packages/helm/project-smarter/smarter>`_.
  - Manage AI resources with the :doc:`web dashboard <smarter-framework/developer-reference/react-integration/smarter-chat>`, the :doc:`REST API <smarter-framework/smarter-api>`, and the :doc:`command-line interface <smarter-platform/cli>`.
  - Keeps track of :doc:`logs <smarter-framework/developer-reference/smarter-journal>`, safety checks, :doc:`costs <smarter-platform/cost-accounting>`, and :doc:`security <smarter-platform/security>` so nothing gets lost or misused.

- **AI Resource Management**

  - Works with many :doc:`AI model providers <smarter-resources/smarter-provider>` — `OpenAI <https://developers.openai.com/api/reference/overview/>`_, `Google AI <https://ai.google.dev/api>`_, `Meta AI <https://developers.facebook.com/docs/>`_, `DeepSeek <https://api-docs.deepseek.com/>`_, and others.
  - Lets you :doc:`organize <smarter-resources/smarter-chatbot>` and version your prompts, and see how they change over time.
  - Supports “:doc:`agents <smarter-resources/smarter-plugin>`” and multi-step AI workflows so you can build bigger, smarter tasks.
  - Secure integrations to :doc:`external data sources <smarter-resources/smarter-plugin>` like :doc:`databases <smarter-resources/plugins/plugin/sql>` and :doc:`APIs <smarter-resources/plugins/plugin/api>`.

- **Developer Application Framework**

  - Built on :doc:`Django <smarter-framework/developer-reference/lib/django>`, :doc:`Django REST Framework <smarter-framework/developer-reference/lib/drf>`, :doc:`Pydantic <smarter-framework/technologies/pydantic>`.
  - Automated :doc:`AWS cloud infrastructure <smarter-framework/technologies/aws>` and :doc:`Kubernetes <smarter-framework/technologies/kubernetes>` management.
  - ReactJS component-based :doc:`UI integration solution <smarter-framework/developer-reference/react-integration/smarter-chat>` that works for any web page.
  - Build AI tools that connect to enterprise resources like :doc:`Sql databases <smarter-resources/plugins/plugin/sql>` and :doc:`REST APIs <smarter-resources/plugins/plugin/api>`.
  - :doc:`Prompt engineer workbench <smarter-framework/developer-reference/react-integration/smarter-chat>` for testing prompts and workflows before you deploy.
  - Vibrant developer community: `PyPI <https://pypi.org/project/smarter-api/>`_, `NPM <https://www.npmjs.com/package/@smarter.sh/ui-chat>`_, `VS Code extensions <https://marketplace.visualstudio.com/items?itemName=querium.smarter-manifest>`_, and more.


Usage
------

**1. Create a Smarter manifest**

.. literalinclude:: ../../smarter/smarter/apps/plugin/data/stackademy/stackademy-chatbot-sql.yaml
   :language: yaml
   :caption: Example Smarter Manifest


**2. Apply the Manifest**

.. code-block:: console

   smarter apply -f stackademy-chatbot-sql.yaml

**3. Interact with the Chatbot**

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

.. toctree::
   :maxdepth: 1
   :caption: External Resources

   external-links/support-smarter
   external-links/swagger
   external-links/manifest-reference
   external-links/json-schemas
   external-links/youtube
