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


A `declarative <smarter-framework/pydantic/smarter-manifests.rst>`_ AI resource management `platform <smarter-platform.rst>`_ and `developer framework <smarter-framework.rst>`_.

- **From scratch** | :doc:`smarter-platform/quick-start` | :doc:`smarter-platform/prerequisites` | :doc:`smarter-platform/trouble-shooting` | `Tutorial <https://platform.smarter.sh/docs/learn/>`__
- **Platform**

  - Helps you manage all your :doc:`AI resources <smarter-resources>` using easy YAML files (like how `Kubernetes <https://kubernetes.io/>`_ works).
  - Installs quickly using `Docker <https://hub.docker.com/r/mcdaniel0073/smarter>`_, and can also run on Kubernetes with the `official Smarter Helm chart <https://artifacthub.io/packages/search?repo=project-smarter>`_.
  - Gives you three ways to manage resources: a web dashboard, a :doc:`REST API <smarter-framework/smarter-api>`, and a :doc:`command-line tool <smarter-platform/cli>`.
  - Keeps track of :doc:`logs <smarter-framework/smarter-journal>`, safety checks, :doc:`costs <smarter-platform/cost-accounting>`, and :doc:`security <smarter-platform/security>` so nothing gets lost or misused.

- **AI Resource Management**

  - Works with many :doc:`AI model providers <smarter-resources/smarter-provider>` — `OpenAI <https://platform.openai.com/docs/api-reference/>`_, `Google AI <https://ai.google.dev/api>`_, `Meta AI <https://developers.facebook.com/docs/>`_, `DeepSeek <https://api-docs.deepseek.com/>`_, and others.
  - Lets you :doc:`organize <smarter-resources/smarter-chatbot>` and version your prompts, and see how they change over time.
  - Supports “:doc:`agents <smarter-resources/smarter-plugin>`” and multi-step AI workflows so you can build bigger, smarter tasks.
  - Integrates with :doc:`external data sources <smarter-resources/smarter-plugin>` like :doc:`databases <smarter-resources/plugins/plugin/sql>` and :doc:`APIs <smarter-resources/plugins/plugin/api>` to give your AI access to up-to-date information.

- **Application Development Framework**

  - Built on :doc:`Django <smarter-framework/django>`, :doc:`Django REST Framework <smarter-framework/drf>`, and :doc:`Pydantic <smarter-framework/pydantic>`.
  - Lets you build your own tools to connect the AI to things like :doc:`enterprise databases <smarter-resources/plugins/plugin/sql>` and :doc:`APIs <smarter-resources/plugins/plugin/api>`.
  - Includes a :doc:`workbench <smarter-resources/chatbots/react-ui>` for testing prompts and building your AI flows before you deploy them.
  - Has a vibrant developer community: packages on `PyPI <https://pypi.org/project/smarter-api/>`_, `NPM <https://www.npmjs.com/package/@smarter.sh/ui-chat>`_, `VS Code extensions <https://marketplace.visualstudio.com/items?itemName=querium.smarter-manifest>`_, and more.


Usage
------

**1. Create a Smarter manifest**

.. literalinclude:: ../../smarter/smarter/apps/plugin/data/stackademy/chatbot-stackademy-sql.yaml
   :language: yaml
   :caption: Example Smarter Manifest


**2. Apply the Manifest**

.. code-block:: console

   smarter apply -f stackademy_chatbot.yaml

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
   external-links/smarter-docs
   external-links/swagger
   external-links/redoc
   external-links/manifest-reference
   external-links/json-schemas
   external-links/smarter-tutorial
   external-links/youtube
