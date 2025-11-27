.. Smarter documentation master file, created by
   sphinx-quickstart on Mon Nov 24 20:56:57 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Smarter
=======

.. image:: https://img.shields.io/badge/Website-smarter.sh-brightgreen
   :target: https://smarter.sh
   :alt: Project Website

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


An extensible AI resource management system.

Features
--------

- Declarative `YAML manifest-based <https://platform.smarter.sh/docs/manifests/>`__ resource management that works like Kubernetes' kubectl.
- Easy `Docker-based <https://hub.docker.com/r/mcdaniel0073/smarter>`__ installation for Windows, macOS and Linux. See the `Smarter Helm chart <https://artifacthub.io/packages/helm/project-smarter/smarter>`__ for native Kubernetes support.
- Supports a growing list of LLM providers: DeepSeek, OpenAI, Google AI, Meta AI, and more.
- Web console, REST API, and CLI (downloadable at `smarter.sh/cli <https://smarter.sh/cli>`__).
- Extensibility model for LLM tool calls for integrating remote data sources like SQL databases and remote APIs. See :doc:`developers/architecture/plugin`.
- Agentic workflow support for building multi-step AI processes.
- Robust prompt management with versioning, testing, and deployment tracking.
- Built-in prompt content moderation, detailed logging, security, cost accounting, and audit features.
- Prompt engineering workbench for designing, testing, deploying, and managing AI resources.
- Thriving developer ecosystem: `PyPi <https://pypi.org/project/smarter-api/>`__, `NPM <https://www.npmjs.com/package/@smarter.sh/ui-chat>`__, `VS Code Extension <https://marketplace.visualstudio.com/items/?itemName=Querium.smarter-manifest>`__, `Homebrew <https://smarter.sh/cli>`__, `Chocolately <https://smarter.sh/cli>`__ and more.

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



Quickstart
----------

You'll be up and running on your desktop in about 10 minutes!

**1. Install Docker Desktop.**
If you haven't already, download and install `Docker Desktop <https://docs.docker.com/desktop/>`__. This will also install Docker Compose.

**2. Clone the Repository.**
Open your terminal (command prompt) and run the following commands:

.. code-block:: console

   git clone https://github.com/smarter-sh/smarter-deploy.git
   cd smarter-deploy


**3. Prepare Your Environment File.**
Smarter requires a .env file with your credentials and configuration. You can scaffold a template using the following command:

.. code-block:: console

   make                # creates a .env file in the root of the repo

.. note::

   Open the newly created .env file and add your credentials (API keys, passwords, etc.) as needed. The application will not run without this step.
   Note that `.env` contains copious inline documentation that you can refer to for specific configuration and technical guidance.

**4. Initialize the Application.**
This step pulls the Docker containers, and seeds the platform with test data:

.. code-block:: console

  make init


**5. Start the Application.**
Run the following command to start all Docker containers and launch the web server:

.. code-block:: console

  make run

The web console will be available at: http://127.0.0.1:8000/ or http://localhost:8000
If you see a login screen, your deployment is working!

.. raw:: html

   <img src="https://cdn.smarter.sh/images/smarter-login-screen.png"
        style="width: 100%; height: auto; display: block; margin: 0 0 1.5em 0; border-radius: 0;"
        alt="Smarter Login Screen"/>



**6. Log In.**
Go to http://localhost:8000/login/ and log in with:

Username: admin@smarter.sh
Password: smarter

.. note::
   For security reasons, be sure to change the default password after your first login.

**7. Download the Smarter Command-Line Interface.**
You'll need to download, install and configure the cli in order to manage AI resources. Get the cli here: `smarter.sh/cli <https://smarter.sh/cli>`__.

Prerequisites
-------------

Before you begin, make sure you have:

- 20Gib of available drive space
- for Mac: Version 12 (Monterey), Apple Silicon (M1 or newer) or Intel CPU with support for virtualization
- for Windows: Windows 10 64-bit, 64-bit processor with Second Level Address Translation (SLAT), 8Gib of RAM, Windows Subsystem for Linux 2 if running Windows Home Editions.
- `Docker Desktop <https://www.docker.com/products/docker-desktop/>`__ installed and running (includes Docker Compose)
- Basic familiarity with using the terminal/command prompt
- (Optional) A Git client if you want to clone this repository

Troubleshooting & FAQ
---------------------

.. rubric:: Frequently Asked Questions

**Q: Docker not running?**
A: Make sure Docker Desktop is open and running before you use any make commands.

**Q: Port already in use?**
A: If you get an error about port 8000, make sure nothing else is running on that port, or change the port in your .env and Docker configuration.

**Q: .env file issues?**
A: Double-check that your .env file exists in the project root and contains all required variables.

**Q: Still stuck?**
A:
- Verify that `OPENAI_API_KEY` has been set in your .env file in the root of the repository.
- Try running `docker compose ps` to see the status of your containers.
- Check the Docker Desktop dashboard for error logs.
- Ask for help: `Lawrence McDaniel <https://lawrencemcdaniel.com>`__

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   system-management
   smarter-resources
   developers
   integrations
   adr

.. toctree::
   :maxdepth: 2
   :caption: External Resources

   external-links/smarter-docs
   external-links/swagger
   external-links/redoc
   external-links/manifest-reference
   external-links/json-schemas
   external-links/smarter-tutorial
   external-links/youtube
