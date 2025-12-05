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


A declarative AI resource management system and developer framework.

- **From scratch** | :doc:`smarter-platform/quick-start` | :doc:`smarter-platform/prerequisites` | :doc:`smarter-platform/trouble-shooting` | `Tutorial <https://platform.smarter.sh/docs/learn/>`__
- **Platform**

  - Helps you manage all your AI resources using easy YAML files (like how Kubernetes works).
  - Installs quickly using Docker, and can also run on Kubernetes with a Helm chart.
  - Gives you three ways to manage resources: a web dashboard, a REST API, and a command-line tool.
  - Keeps track of logs, safety checks, costs, and security so nothing gets lost or misused.

- **AI Resource Management**

  - Works with many AI model providers — OpenAI, Google, Meta, DeepSeek, and others.
  - Lets you organize and version your prompts, and see how they change over time.
  - Supports “agents” and multi-step AI workflows so you can build bigger, smarter tasks.

- **Application Development Framework**

  - Built on Django, Django REST Framework, and Pydantic.
  - Lets you build your own tools to connect the AI to things like enterprise databases and APIs.
  - Includes a workbench for testing prompts and building your AI flows before you deploy them.
  - Has a vibrant developer community: packages on PyPI, NPM, VS Code extensions, and more.


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
